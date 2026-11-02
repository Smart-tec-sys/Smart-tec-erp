"""Testes ASGI/driver simulados; proibido conectar ou aplicar SQL real."""

import asyncio
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from fastapi import FastAPI
from psycopg2.extensions import TRANSACTION_STATUS_IDLE, TRANSACTION_STATUS_INTRANS

from app.routes.diagnostico import router
from app.services import phase1_up as servico


class Phase1UpTests(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": "token-sintetico"})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        for metodo in ("connect", "raw_connection"):
            bloqueio = patch(
                "sqlalchemy.engine.Engine." + metodo,
                side_effect=AssertionError("Banco real proibido"),
            )
            bloqueio.start()
            self.addCleanup(bloqueio.stop)
        self.app = FastAPI()
        self.app.include_router(router)
        self.sql, self.colunas = servico._ler_sql_validado()
        self.engine = Mock()
        self.pool = Mock()
        self.driver = Mock()
        self.cursor = Mock()
        self.cursor.__enter__ = Mock(return_value=self.cursor)
        self.cursor.__exit__ = Mock(return_value=False)
        self.engine.raw_connection.return_value = self.pool
        self.pool.driver_connection = self.driver
        self.driver.cursor.return_value = self.cursor
        self.driver.get_transaction_status.side_effect = lambda: self.estado
        self.driver.rollback.side_effect = self.rollback
        self.cursor.execute.side_effect = self.executar
        self.cursor.fetchone.side_effect = lambda: self.resultado
        self.cursor.fetchall.side_effect = lambda: self.resultados
        self.estado = TRANSACTION_STATUS_IDLE
        self.commit = False
        self.resultado = None
        self.resultados = []
        self.baseline = servico._CONTAGENS + (False, False, False)
        self.destino = servico._DESTINO
        self.contagens = servico._CONTAGENS
        self.tabelas = {(t,) for t in servico._TABELAS_NOVAS}
        self.colunas_atuais = set(self.colunas)
        self.indices = [
            (nome, definicao, True, True, True)
            for nome, definicao in servico._INDICES.items()
        ]
        self.erro_sql = None
        self.falha_pos_commit = None
        self.commit_status = "COMMIT"
        self.eventos = []
        troca = patch("app.routes.diagnostico.engine", self.engine)
        troca.start()
        self.addCleanup(troca.stop)

    def rollback(self):
        self.eventos.append(("rollback", self.commit, self.estado))
        self.estado = TRANSACTION_STATUS_IDLE

    def executar(self, sql):
        self.eventos.append(("execute", sql))
        if sql == self.sql:
            self.assertTrue(self.driver.autocommit)
            if self.erro_sql:
                raise self.erro_sql
            self.commit = True
            self.estado = TRANSACTION_STATUS_IDLE
            self.cursor.statusmessage = self.commit_status
        elif sql.startswith("SET TRANSACTION"):
            self.assertFalse(self.driver.autocommit)
            if self.commit and self.falha_pos_commit:
                raise self.falha_pos_commit
            self.estado = TRANSACTION_STATUS_INTRANS
            self.cursor.statusmessage = "SET"
        elif sql.startswith("SET LOCAL"):
            self.cursor.statusmessage = "SET"
        elif sql == servico._SQL_DESTINO:
            self.resultado = self.destino
        elif sql == servico._SQL_BASELINE:
            self.resultado = self.baseline
        elif sql == servico._SQL_CONTAGENS:
            self.resultado = self.contagens
        elif sql == servico._SQL_TABELAS:
            self.resultados = self.tabelas
        elif sql == servico._SQL_COLUNAS:
            self.resultados = self.colunas_atuais
        elif sql == servico._SQL_INDICES:
            self.resultados = self.indices
        else:
            raise AssertionError("SQL fora das consultas fixas")

    def requisitar(self, token="token-sintetico", corpo=None, params=None):
        async def executar():
            mensagens = []

            async def receber():
                return {
                    "type": "http.request",
                    "body": b"" if corpo is None else json.dumps(corpo).encode(),
                    "more_body": False,
                }

            async def enviar(mensagem):
                mensagens.append(mensagem)

            await self.app(
                {
                    "type": "http", "asgi": {"version": "3.0"},
                    "http_version": "1.1", "method": "POST", "scheme": "http",
                    "path": "/diag/run-phase1-up", "raw_path": b"/diag/run-phase1-up",
                    "query_string": urlencode(params or {}).encode(), "root_path": "",
                    "headers": [] if token is None else [
                        (b"x-diagnostic-token", token.encode()),
                    ],
                    "client": ("127.0.0.1", 1), "server": ("test", 80),
                },
                receber, enviar,
            )
            inicio = next(m for m in mensagens if m["type"] == "http.response.start")
            texto = b"".join(
                m.get("body", b"") for m in mensagens if m["type"] == "http.response.body"
            ).decode()
            return SimpleNamespace(
                status_code=inicio["status"], text=texto,
                json=lambda: json.loads(texto),
                headers={k.decode(): v.decode() for k, v in inicio["headers"]},
            )

        return asyncio.run(executar())

    def sql_alterado(self, sql):
        arquivo = Mock()
        arquivo.is_file.return_value = True
        arquivo.read_text.return_value = sql
        return patch.object(servico, "ARQUIVO_UP", arquivo)

    def test_token_ausente_invalido_e_desabilitado(self):
        for token in (None, "incorreto"):
            with self.subTest(token=token):
                self.assertEqual(self.requisitar(token).status_code, 401)
        with patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": ""}):
            self.assertEqual(self.requisitar().status_code, 503)
        self.engine.raw_connection.assert_not_called()

    def test_rejeita_corpo_e_query_params(self):
        for kwargs in (
            {"corpo": {"sql": "COMMIT", "filename": "outro.sql"}},
            {"corpo": {}},
            {"params": {"filename": "outro.sql"}},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.requisitar(**kwargs).status_code, 400)
        self.engine.raw_connection.assert_not_called()

    def test_arquivo_inexistente(self):
        with patch.object(servico, "ARQUIVO_UP") as arquivo:
            arquivo.is_file.return_value = False
            self.assertEqual(self.requisitar().status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_adulteracao_sha256_bloqueada(self):
        with self.sql_alterado(self.sql.replace("CREATE TABLE", "CREATE UNLOGGED TABLE", 1)):
            resposta = self.requisitar()
            self.assertEqual(resposta.status_code, 500)
            self.assertIn("SHA-256", resposta.text)
        self.engine.raw_connection.assert_not_called()

    def test_rollback_indevido_e_commit_ausente_ou_extra(self):
        for sql in (
            self.sql.replace("COMMIT;", "ROLLBACK;"),
            self.sql.replace("BEGIN;", "BEGIN; ROLLBACK;", 1),
            self.sql.replace("COMMIT;", "-- COMMIT;"),
            self.sql.replace("BEGIN;", "BEGIN; COMMIT;", 1),
            self.sql.replace("RAISE EXCEPTION", "ROLLBACK; RAISE EXCEPTION", 1),
        ):
            with self.subTest(sql=sql[-30:]), self.sql_alterado(sql):
                self.assertEqual(self.requisitar().status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_guardas_banco_e_usuario_obrigatorias(self):
        for sql in (
            self.sql.replace("current_database()", "outro_banco()"),
            self.sql.replace("current_user", "session_user"),
        ):
            with self.subTest(sql=sql[:30]), self.sql_alterado(sql):
                self.assertEqual(self.requisitar().status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_baseline_divergente_aborta_antes_ddl(self):
        for indice in range(9):
            valores = list(servico._CONTAGENS + (False, False, False))
            valores[indice] = 2 if indice < 6 else True
            self.baseline = tuple(valores)
            with self.subTest(indice=indice):
                resposta = self.requisitar()
                self.assertEqual(resposta.status_code, 500)
                self.assertIn("BaselineUpDivergente", resposta.text)
                self.assertFalse(self.commit)
        self.assertNotIn(self.sql, [c.args[0] for c in self.cursor.execute.call_args_list])

    def test_destino_divergente_aborta_antes_baseline_e_ddl(self):
        for destino in (("outro", "smarttec_staging"), ("smarttec_erp_staging", "outro")):
            self.destino = destino
            with self.subTest(destino=destino):
                self.assertEqual(self.requisitar().status_code, 500)
        sqls = [c.args[0] for c in self.cursor.execute.call_args_list]
        self.assertNotIn(servico._SQL_BASELINE, sqls)
        self.assertNotIn(self.sql, sqls)

    def test_sucesso_valida_5_tabelas_62_colunas_e_indices(self):
        self.colunas_atuais.add(("clientes", "campo_antigo", "text"))
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json(), {
            "ok": True, "database": "smarttec_erp_staging",
            "message": "FASE 1 NUCLEO COMERCIAL aplicada com sucesso",
            "tables_created": 5, "phase1_columns_validated": 62,
        })
        self.assertEqual(len(self.colunas), 62)
        for coluna in (
            ("orcamentos", "observacao_interna", "text"),
            ("orcamentos_itens", "dados_tecnicos", "jsonb"),
            ("orcamentos", "cliente_final_nome", "text"),
            ("pedidos", "orcamento_id", "integer"),
        ):
            self.assertIn(coluna, self.colunas)
        sqls = [c.args[0] for c in self.cursor.execute.call_args_list]
        self.assertEqual(sqls.count(self.sql), 1)
        self.assertLess(sqls.index(servico._SQL_BASELINE), sqls.index(self.sql))
        self.assertLess(sqls.index(self.sql), sqls.index(servico._SQL_COLUNAS))
        self.assertEqual(resposta.headers["cache-control"], "no-store")
        self.assertFalse(self.driver.autocommit)
        self.pool.close.assert_called_once()
        self.driver.commit.assert_not_called()
        for evento in self.eventos:
            if evento[0] == "rollback" and evento[1]:
                self.assertEqual(evento[2], TRANSACTION_STATUS_INTRANS)

    def test_falha_execucao_sanitizada_sem_alegar_sucesso(self):
        self.erro_sql = RuntimeError("postgresql://usuario:senha@host/db token-sintetico")
        with self.assertLogs("app.routes.diagnostico", level="ERROR") as logs:
            resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("COMMIT nao confirmado", resposta.text)
        for segredo in ("postgresql://", "senha", "token-sintetico"):
            self.assertNotIn(segredo, resposta.text)
            self.assertNotIn(segredo, " ".join(logs.output))
        self.pool.close.assert_called_once()
        self.assertFalse(self.commit)
        self.assertNotIn(servico._SQL_COLUNAS, [c.args[0] for c in self.cursor.execute.call_args_list])

    def test_divergencia_pos_commit_erro_grave_sem_desfazer_aplicacao(self):
        self.tabelas.remove(("representantes",))
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("ERRO GRAVE", resposta.text)
        self.assertIn("COMMIT confirmado", resposta.text)
        self.assertTrue(self.commit)
        for evento in self.eventos:
            if evento[0] == "rollback" and evento[1]:
                self.assertEqual(evento[2], TRANSACTION_STATUS_INTRANS)
        self.driver.commit.assert_not_called()

    def test_todas_62_colunas_e_tipos_sao_verificados(self):
        for coluna in self.colunas:
            for alterar_tipo in (False, True):
                self.colunas_atuais = self.colunas - {coluna}
                if alterar_tipo:
                    self.colunas_atuais.add((coluna[0], coluna[1], "tipo_incorreto"))
                with self.subTest(coluna=coluna, tipo=alterar_tipo):
                    resposta = self.requisitar()
                    self.assertEqual(resposta.status_code, 500)
                    self.assertIn("ERRO GRAVE", resposta.text)

    def test_todas_tabelas_e_contagens_verificadas_pos_commit(self):
        for tabela in servico._TABELAS_NOVAS:
            self.tabelas = {(t,) for t in servico._TABELAS_NOVAS - {tabela}}
            with self.subTest(tabela=tabela):
                self.assertEqual(self.requisitar().status_code, 500)
        self.tabelas = {(t,) for t in servico._TABELAS_NOVAS}
        for indice in range(6):
            valores = list(servico._CONTAGENS)
            valores[indice] = 9
            self.contagens = tuple(valores)
            with self.subTest(indice=indice):
                self.assertEqual(self.requisitar().status_code, 500)

    def test_indices_ausentes_invalidos_e_definicao_divergente(self):
        for nome, definicao in servico._INDICES.items():
            for metadados in (
                None, ("outro indice", True, True, True),
                (definicao, False, True, True),
                (definicao, True, False, True),
                (definicao, True, True, False),
            ):
                self.indices = [
                    (n, d, True, True, True) for n, d in servico._INDICES.items() if n != nome
                ]
                if metadados:
                    self.indices.append((nome, *metadados))
                with self.subTest(nome=nome, metadados=metadados):
                    self.assertEqual(self.requisitar().status_code, 500)

    def test_erro_leitura_pos_commit_identifica_aplicacao_confirmada(self):
        self.falha_pos_commit = RuntimeError("senha-secreta token-sintetico")
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("COMMIT confirmado", resposta.text)
        self.assertNotIn("senha-secreta", resposta.text)
        self.assertNotIn("token-sintetico", resposta.text)
        self.assertTrue(self.commit)
        # Nenhuma transacao de verificacao chegou a iniciar.
        self.assertFalse(any(e[0] == "rollback" and e[1] for e in self.eventos))

    def test_commit_nao_confirmado_exige_verificar_antes_de_repetir(self):
        self.commit_status = "DO"
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("incerto", resposta.text)

    def test_falha_limpeza_pos_commit_erro_grave(self):
        def rollback():
            if self.commit:
                raise RuntimeError("senha-secreta")
            self.rollback()

        self.driver.rollback.side_effect = rollback
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("ERRO GRAVE", resposta.text)
        self.assertNotIn("senha-secreta", resposta.text)
        self.pool.invalidate.assert_called_once()
        self.pool.close.assert_called_once()

    def test_falha_close_pos_commit_erro_grave(self):
        self.pool.close.side_effect = RuntimeError("senha-secreta")
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("ERRO GRAVE", resposta.text)
        self.assertNotIn("senha-secreta", resposta.text)

    def test_falha_baseline_sql_e_conexao_sanitizadas(self):
        self.cursor.execute.side_effect = RuntimeError("postgresql://usuario:senha@host/db token-sintetico")
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("aplicacao nao iniciada", resposta.text)
        self.assertNotIn("senha", resposta.text)
        self.assertFalse(self.commit)
        self.pool.close.assert_called_once()
        self.engine.raw_connection.side_effect = RuntimeError("senha token-sintetico")
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertNotIn("senha", resposta.text)
        self.assertNotIn("token-sintetico", resposta.text)

    def test_falha_invalidacao_preserva_erro_grave(self):
        def rollback():
            if self.commit:
                raise RuntimeError("senha-secreta")
            self.rollback()

        self.driver.rollback.side_effect = rollback
        self.pool.invalidate.side_effect = RuntimeError("token-sintetico")
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertIn("ERRO GRAVE", resposta.text)
        self.assertNotIn("senha-secreta", resposta.text)
        self.assertNotIn("token-sintetico", resposta.text)
        self.pool.close.assert_called_once()

    def test_crlf_mantem_hash_revisado(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "up.sql"
            arquivo.write_bytes(self.sql.replace("\n", "\r\n").encode("utf-8"))
            with patch.object(servico, "ARQUIVO_UP", arquivo):
                self.assertEqual(servico._ler_sql_validado(), (self.sql, self.colunas))


if __name__ == "__main__":
    unittest.main()
