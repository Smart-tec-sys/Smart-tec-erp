"""Diagnostico temporario: ASGI em memoria, sem conexoes ou SQL reais."""

import asyncio
import json
import os
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.diagnostico import router


class DiagnosticoDestinoBancoTest(unittest.TestCase):
    def setUp(self):
        self.ambiente = patch.dict(
            os.environ, {"DIAG_DB_TARGET_TOKEN": "token-apenas-para-teste"}
        )
        self.ambiente.start()
        self.addCleanup(self.ambiente.stop)
        self.bloqueio = patch(
            "sqlalchemy.engine.Engine.connect",
            side_effect=AssertionError("Conexao real proibida neste teste"),
        )
        self.bloqueio.start()
        self.addCleanup(self.bloqueio.stop)

        self.db = Mock(spec=Session)
        self.provedor = Mock(return_value=self.db)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_db] = lambda: self.provedor()
        self.dados = {
            "database": "smarttec_erp_beta",
            "schema": "public",
            "user": "usuario_diagnostico",
            "server_addr": "127.0.0.1",
            "server_port": 5432,
            "search_path": '"$user", public',
            "representantes_exists": True,
            "orcamentos_exists": True,
            "cliente_final_nome_exists": False,
        }
        self.resultado = Mock()
        self.resultado.mappings.return_value.one.return_value = self.dados
        self.db.execute.side_effect = [Mock(), self.resultado]

    def requisitar(self, token=None, caminho="/diag/db-target"):
        async def executar():
            mensagens = []
            entregue = False

            async def receber():
                nonlocal entregue
                if entregue:
                    return {"type": "http.disconnect"}
                entregue = True
                return {"type": "http.request", "body": b"", "more_body": False}

            async def enviar(mensagem):
                mensagens.append(mensagem)

            cabecalhos = []
            if token is not None:
                cabecalhos.append((b"x-diagnostic-token", token))
            await self.app(
                {
                    "type": "http",
                    "asgi": {"version": "3.0"},
                    "http_version": "1.1",
                    "method": "GET",
                    "scheme": "http",
                    "path": caminho,
                    "raw_path": caminho.encode(),
                    "query_string": b"",
                    "root_path": "",
                    "headers": cabecalhos,
                    "client": ("127.0.0.1", 1),
                    "server": ("test", 80),
                },
                receber,
                enviar,
            )
            inicio = next(
                m for m in mensagens if m["type"] == "http.response.start"
            )
            corpo = b"".join(
                m.get("body", b"")
                for m in mensagens
                if m["type"] == "http.response.body"
            )
            return inicio["status"], dict(inicio["headers"]), json.loads(corpo)

        return asyncio.run(executar())

    def test_sem_configuracao_fica_desabilitado_sem_obter_sessao(self):
        for valor in ("", "   "):
            with self.subTest(valor=valor):
                os.environ["DIAG_DB_TARGET_TOKEN"] = valor
                status, _, _ = self.requisitar(b"token-apenas-para-teste")
                self.assertEqual(status, 503)
                self.provedor.assert_not_called()
                self.db.execute.assert_not_called()

    def test_token_ausente_incorreto_ou_nao_ascii_nao_obtem_sessao(self):
        for token in (None, b"incorreto", b"\xff"):
            with self.subTest(token=token):
                status, _, corpo = self.requisitar(token)
                self.assertEqual(status, 401)
                self.assertEqual(corpo["detail"], "acesso diagnóstico não autorizado")
                self.provedor.assert_not_called()
                self.db.execute.assert_not_called()

    def test_autorizado_retorna_apenas_metadados_e_faz_rollback(self):
        status, cabecalhos, corpo = self.requisitar(b"token-apenas-para-teste")
        self.assertEqual(status, 200)
        self.assertEqual(corpo, self.dados)
        self.assertEqual(len(corpo), 9)
        self.assertEqual(cabecalhos[b"cache-control"], b"no-store")
        self.provedor.assert_called_once_with()
        comandos = [str(chamada.args[0]) for chamada in self.db.execute.call_args_list]
        self.assertEqual(comandos[0], "SET TRANSACTION READ ONLY")
        self.assertTrue(comandos[1].lstrip().startswith("SELECT"))
        self.assertEqual(len(comandos), 2)
        self.db.rollback.assert_called_once_with()
        for metodo in ("commit", "add", "add_all", "delete", "flush"):
            getattr(self.db, metodo).assert_not_called()

    def test_erro_na_consulta_nao_expoe_detalhes_e_faz_rollback(self):
        segredo = "postgresql://privado:senha-secreta@servidor-interno/banco"
        self.db.execute.side_effect = [Mock(), SQLAlchemyError(segredo)]
        with patch("logging.Logger._log") as registrar:
            status, _, corpo = self.requisitar(b"token-apenas-para-teste")
        self.assertEqual(status, 503)
        self.assertEqual(corpo, {"detail": "diagnóstico de banco indisponível"})
        self.assertNotIn(segredo, json.dumps(corpo))
        registrar.assert_not_called()
        self.db.rollback.assert_called_once_with()
        self.db.commit.assert_not_called()

    def test_erro_ao_ativar_somente_leitura_nao_executa_consulta(self):
        self.db.execute.side_effect = SQLAlchemyError("detalhes privados")
        status, _, corpo = self.requisitar(b"token-apenas-para-teste")
        self.assertEqual(status, 503)
        self.assertEqual(corpo, {"detail": "diagnóstico de banco indisponível"})
        self.assertEqual(self.db.execute.call_count, 1)
        self.db.rollback.assert_called_once_with()

    def test_erro_no_rollback_tambem_fica_sanitizado(self):
        self.db.rollback.side_effect = SQLAlchemyError("detalhes privados")
        status, _, corpo = self.requisitar(b"token-apenas-para-teste")
        self.assertEqual(status, 503)
        self.assertEqual(corpo, {"detail": "diagnóstico de banco indisponível"})
        self.db.commit.assert_not_called()

    def test_rota_temporaria_nao_aparece_no_openapi(self):
        status, _, corpo = self.requisitar(caminho="/openapi.json")
        self.assertEqual(status, 200)
        self.assertNotIn("/diag/db-target", corpo["paths"])
        self.provedor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
