"""Rota temporaria e executor com driver simulado; conexoes reais proibidas."""

import asyncio
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from urllib.parse import urlencode
from unittest.mock import Mock, patch

from fastapi import FastAPI
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from app.routes.diagnostico import router
from app.services import phase1_dry_run as servico


class Phase1DryRunTests(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": "token-sintetico"})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        for metodo in ("connect", "raw_connection"):
            bloqueio = patch(
                "sqlalchemy.engine.Engine." + metodo,
                side_effect=AssertionError("Banco real proibido nos testes"),
            )
            bloqueio.start()
            self.addCleanup(bloqueio.stop)
        app = FastAPI()
        app.include_router(router)
        self.app = app
        self.sql = servico.ARQUIVO_DRY_RUN.read_text(encoding="utf-8")
        self.cursor = Mock()
        self.cursor.__enter__ = Mock(return_value=self.cursor)
        self.cursor.__exit__ = Mock(return_value=False)
        self.cursor.fetchone.side_effect = [
            ("smarttec_erp_staging", "smarttec_staging"),
            ("smarttec_erp_staging", "smarttec_staging", False, False, False, 1, 0),
        ]
        self.cursor.statusmessage = "ROLLBACK"
        self.conexao = Mock()
        self.pool = Mock()
        self.pool.driver_connection = self.conexao
        self.conexao.cursor.return_value = self.cursor
        self.conexao.get_transaction_status.return_value = TRANSACTION_STATUS_IDLE
        self.conexao.notices = []

        def executar(sql):
            if sql == self.sql:
                self.assertTrue(self.conexao.autocommit)
                self.conexao.notices.append("NOTICE: " + servico._AVISO_FINAL)
            if sql == servico._SQL_POS_ROLLBACK:
                self.assertFalse(self.conexao.autocommit)

        self.cursor.execute.side_effect = executar
        engine = Mock()
        engine.raw_connection.return_value = self.pool
        troca = patch("app.routes.diagnostico.engine", engine)
        troca.start()
        self.addCleanup(troca.stop)
        self.engine = engine

    def requisitar(self, token="token-sintetico", **kwargs):
        async def executar():
            mensagens = []
            entregue = False

            async def receber():
                nonlocal entregue
                if entregue:
                    return {"type": "http.disconnect"}
                entregue = True
                corpo = json.dumps(kwargs["json"]).encode() if "json" in kwargs else b""
                return {"type": "http.request", "body": corpo, "more_body": False}

            async def enviar(mensagem):
                mensagens.append(mensagem)

            await self.app(
                {
                    "type": "http", "asgi": {"version": "3.0"},
                    "http_version": "1.1", "method": "POST", "scheme": "http",
                    "path": "/diag/run-phase1-dry-run",
                    "raw_path": b"/diag/run-phase1-dry-run",
                    "query_string": urlencode(kwargs.get("params", {})).encode(),
                    "root_path": "",
                    "headers": [] if token is None else [
                        (b"x-diagnostic-token", token.encode()),
                    ],
                    "client": ("127.0.0.1", 1), "server": ("test", 80),
                },
                receber, enviar,
            )
            inicio = next(m for m in mensagens if m["type"] == "http.response.start")
            corpo = b"".join(
                m.get("body", b"") for m in mensagens if m["type"] == "http.response.body"
            ).decode()
            return SimpleNamespace(
                status_code=inicio["status"], text=corpo,
                headers={k.decode(): v.decode() for k, v in inicio["headers"]},
                json=lambda: json.loads(corpo),
            )

        return asyncio.run(executar())

    def sql_alterado(self, sql):
        arquivo = Mock()
        arquivo.is_file.return_value = True
        arquivo.read_text.return_value = sql
        return patch.object(servico, "ARQUIVO_DRY_RUN", arquivo)

    def test_token_ausente_e_invalido(self):
        for token in (None, "incorreto"):
            with self.subTest(token=token):
                self.assertEqual(self.requisitar(token).status_code, 401)
        self.engine.raw_connection.assert_not_called()

    def test_token_nao_configurado_desabilita(self):
        with patch.dict(os.environ, {"DIAG_DB_TARGET_TOKEN": ""}):
            self.assertEqual(self.requisitar().status_code, 503)
        self.engine.raw_connection.assert_not_called()

    def test_arquivo_inexistente(self):
        with patch.object(servico, "ARQUIVO_DRY_RUN") as arquivo:
            arquivo.is_file.return_value = False
            resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_commit_executavel_proibido(self):
        for sql in (
            self.sql.replace("ROLLBACK;", "COMMIT;"),
            self.sql.replace("BEGIN;", "BEGIN; COMMIT;", 1),
            self.sql.replace("RAISE NOTICE", "COMMIT; RAISE NOTICE"),
        ):
            with self.subTest(sql=sql[-30:]), self.sql_alterado(sql):
                resposta = self.requisitar()
                self.assertEqual(resposta.status_code, 500)
                self.assertIn("COMMIT executavel", resposta.json()["detail"]["message"])
        self.engine.raw_connection.assert_not_called()

    def test_rollback_ausente_ou_apenas_em_comentario(self):
        for fim in ("", "-- ROLLBACK;"):
            with self.subTest(fim=fim), self.sql_alterado(self.sql.replace("ROLLBACK;", fim)):
                self.assertEqual(self.requisitar().status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_guarda_aviso_e_adulteracao_bloqueiam(self):
        for sql in (
            self.sql.replace("current_database()", "outra_funcao()"),
            self.sql.replace(servico._AVISO_FINAL, "sem aviso"),
            self.sql.replace("CREATE TABLE", "CREATE UNLOGGED TABLE", 1),
        ):
            with self.subTest(sql=sql[:30]), self.sql_alterado(sql):
                self.assertEqual(self.requisitar().status_code, 500)
        self.engine.raw_connection.assert_not_called()

    def test_sucesso_executa_arquivo_integral_e_confere_reversao(self):
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json(), {
            "ok": True, "database": "smarttec_erp_staging",
            "message": "DRY RUN FASE 1 concluido com sucesso e revertido",
        })
        sqls = [c.args[0] for c in self.cursor.execute.call_args_list]
        self.assertIn(self.sql, sqls)
        self.assertIn("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY", sqls)
        self.assertEqual(sqls[-1], servico._SQL_POS_ROLLBACK)
        self.conexao.rollback.assert_called()
        self.pool.close.assert_called_once()
        self.assertFalse(self.conexao.autocommit)
        self.assertEqual(resposta.headers["cache-control"], "no-store")

    def test_crlf_preserva_identidade(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "dry_run.sql"
            arquivo.write_bytes(self.sql.replace("\n", "\r\n").encode("utf-8"))
            with patch.object(servico, "ARQUIVO_DRY_RUN", arquivo):
                self.assertEqual(servico._ler_sql_validado(), self.sql)

    def test_erro_execucao_sanitizado_e_conexao_revertida(self):
        segredo = "postgresql://usuario:senha@servidor/banco token-sintetico"
        self.cursor.execute.side_effect = RuntimeError(segredo)
        with self.assertLogs("app.routes.diagnostico", level="ERROR") as logs:
            resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(resposta.json()["detail"]["error_type"], "RuntimeError")
        for valor in ("postgresql://", "senha", "token-sintetico"):
            self.assertNotIn(valor, resposta.text)
            self.assertNotIn(valor, " ".join(logs.output))
        self.conexao.rollback.assert_called()
        self.pool.close.assert_called_once()

    def test_destino_incorreto_nao_executa_ddl(self):
        self.cursor.fetchone.side_effect = [("outro", "smarttec_staging")]
        self.assertEqual(self.requisitar().status_code, 500)
        self.cursor.execute.assert_called_once()
        self.pool.close.assert_called_once()

    def test_alteracao_persistente_erro_grave(self):
        for indice, valor in ((2, True), (3, True), (4, True), (5, 2), (6, 1)):
            resultado = ["smarttec_erp_staging", "smarttec_staging", False, False, False, 1, 0]
            resultado[indice] = valor
            self.cursor.fetchone.side_effect = [
                ("smarttec_erp_staging", "smarttec_staging"), tuple(resultado),
            ]
            with self.subTest(indice=indice):
                resposta = self.requisitar()
                self.assertEqual(resposta.status_code, 500)
                self.assertIn("ERRO GRAVE", resposta.text)

    def test_rollback_e_aviso_devem_ser_confirmados(self):
        self.cursor.statusmessage = "DO"
        self.assertEqual(self.requisitar().status_code, 500)
        self.cursor.statusmessage = "ROLLBACK"
        self.cursor.fetchone.side_effect = [("smarttec_erp_staging", "smarttec_staging")]
        self.cursor.execute.side_effect = None
        self.assertEqual(self.requisitar().status_code, 500)

    def test_requisicao_nao_escolhe_sql_ou_arquivo(self):
        resposta = self.requisitar(
            json={"sql": "COMMIT", "file": "UP.sql"},
            params={"filename": "UP.sql"},
        )
        self.assertEqual(resposta.status_code, 400)
        self.engine.raw_connection.assert_not_called()

    def test_falha_limpeza_invalida_conexao(self):
        self.conexao.rollback.side_effect = [None, RuntimeError("senha-secreta")]
        resposta = self.requisitar()
        self.assertEqual(resposta.status_code, 500)
        self.assertNotIn("senha-secreta", resposta.text)
        self.pool.invalidate.assert_called_once()
        self.pool.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
