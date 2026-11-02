"""Inventario temporario: ASGI e sessoes simuladas, sem banco ou SQL reais."""

import asyncio
import json
import os
import re
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.diagnostico import router


ESPERADAS = {
    "clientes": ["parceiro_id", "representante_id"],
    "orcamentos": [
        "observacao_interna", "parceiro_id", "representante_id",
        "percentual_parceiro", "incluir_rt", "tipo_rt", "percentual_rt",
        "valor_rt", "incluir_taxa_bancaria", "taxa_bancaria_percentual",
        "valor_parceiro", "base_protegida", "valor_taxa_bancaria",
        "total_cliente_final", "vendedor_id", "cliente_final_nome",
        "cliente_final_documento", "cliente_final_telefone",
        "cliente_final_email", "cliente_final_endereco",
    ],
    "orcamentos_itens": ["dados_tecnicos"],
    "pedidos": [
        "orcamento_id", "perfil_comercial", "data_venda", "canal_venda",
        "observacao_interna", "vendedor_id", "parceiro_id", "representante_id",
        "cliente_final_nome", "cliente_final_documento", "cliente_final_telefone",
        "cliente_final_email", "cliente_final_endereco", "percentual_parceiro",
        "incluir_rt", "tipo_rt", "percentual_rt", "valor_rt",
        "incluir_taxa_bancaria", "taxa_bancaria_percentual", "valor_parceiro",
        "valor_taxa_bancaria", "total_cliente_final",
    ],
    "pedidos_itens": [
        "tipo_item", "descricao", "codigo_interno", "grupo_tecnico",
        "modelo_tecnico", "unidade", "largura", "altura", "area",
        "observacao_item", "material", "cor", "acionamento", "lado_comando",
        "calculo_producao_status", "dados_tecnicos",
    ],
}
TABELAS_CONTAGEM = tuple(ESPERADAS) + ("financeiro",)
TABELAS_COMERCIAIS = (
    "parceiros_comerciais", "representantes", "representantes_rt",
    "parceiro_representantes", "parceiro_clientes",
)
VERIFICACOES = (
    "orcamentos_numero_duplicate_groups",
    "pedidos_numero_duplicate_groups",
    "orcamentos_clientes_orphans",
    "orcamentos_itens_orcamentos_orphans",
    "pedidos_itens_pedidos_orphans",
    "financeiro_pedidos_orphans",
    "pedidos_orcamento_duplicate_groups",
)


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
            "database": "smarttec_erp_staging",
            "schema": "public",
            "user": "smarttec_staging",
            "server_addr": "127.0.0.1",
            "server_port": 5432,
            "search_path": '"$user", public',
            "representantes_exists": True,
            "orcamentos_exists": True,
            "cliente_final_nome_exists": True,
        }
        self.schemas = {
            "clientes": ["id", "nome"],
            "orcamentos": ["id", "numero", "cliente_id"],
            "orcamentos_itens": ["id", "orcamento_id"],
            "pedidos": ["id", "numero"],
            "pedidos_itens": ["id", "pedido_id"],
            "financeiro": ["id", "pedido_id"],
        }
        for tabela, colunas in ESPERADAS.items():
            self.schemas[tabela] += colunas
        self.schemas.update({tabela: ["id"] for tabela in TABELAS_COMERCIAIS})
        self.contagens = dict(zip(TABELAS_CONTAGEM, (4, 1, 1, 0, 0, 0)))
        self.problemas = {nome: 0 for nome in VERIFICACOES}
        self.problemas["orcamentos_numero_duplicate_groups"] = 2
        self.problemas["financeiro_pedidos_orphans"] = 3
        self.rls = {"clientes": True}
        self.falha_catalogo = None
        self.falha_agregados = None
        self.db.execute.side_effect = self.executar_simulado

    def linhas_catalogo(self):
        linhas = []
        for tabela, colunas in self.schemas.items():
            for coluna in colunas or [None]:
                linhas.append({
                    "table_name": tabela,
                    "name": coluna,
                    "type": "text" if coluna == "cliente_final_nome" else "integer",
                    "nullable": coluna != "id",
                    "default": "nextval('seq_teste'::regclass)" if coluna == "id" else None,
                    "row_security_active": self.rls.get(tabela, False),
                    "registro_privado": "DADO_PESSOAL_NAO_DEVE_SAIR",
                })
        return linhas

    def executar_simulado(self, comando):
        sql = str(comando)
        resultado = Mock()
        if sql.lstrip().startswith("SET "):
            return resultado
        if "current_database()" in sql:
            resultado.mappings.return_value.one.return_value = dict(self.dados)
            return resultado
        if "pg_attribute" in sql and "pg_class" in sql:
            if self.falha_catalogo:
                raise self.falha_catalogo
            resultado.mappings.return_value.all.return_value = self.linhas_catalogo()
            return resultado
        metricas = re.findall(r"'((?:count|check):[^']+)'", sql)
        if metricas:
            if self.falha_agregados:
                raise self.falha_agregados
            linhas = []
            for metrica in metricas:
                categoria, nome = metrica.split(":", 1)
                valor = self.contagens[nome] if categoria == "count" else self.problemas[nome]
                linhas.append({
                    "metric": metrica,
                    "count": valor,
                    "numero_privado": "NUMERO_PRIVADO_NAO_DEVE_SAIR",
                })
            resultado.mappings.return_value.all.return_value = linhas
            return resultado
        raise AssertionError("Consulta nao reconhecida pelo simulador: " + sql)

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
            inicio = next(m for m in mensagens if m["type"] == "http.response.start")
            corpo = b"".join(
                m.get("body", b"")
                for m in mensagens if m["type"] == "http.response.body"
            )
            return inicio["status"], dict(inicio["headers"]), json.loads(corpo)

        return asyncio.run(executar())

    def autorizado(self):
        status, cabecalhos, corpo = self.requisitar(b"token-apenas-para-teste")
        self.assertEqual(status, 200, corpo)
        return cabecalhos, corpo

    def sql_agregados(self):
        return next(
            str(chamada.args[0])
            for chamada in self.db.execute.call_args_list
            if "'count:" in str(chamada.args[0]) or "'check:" in str(chamada.args[0])
        )

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

    def test_autorizado_retorna_somente_contagens_metadados_e_faz_rollback(self):
        cabecalhos, corpo = self.autorizado()
        self.assertEqual({chave: corpo[chave] for chave in self.dados}, self.dados)
        self.assertEqual(set(corpo), set(self.dados) | {"inventory"})
        self.assertEqual(cabecalhos[b"cache-control"], b"no-store")
        inventario = corpo["inventory"]
        self.assertEqual(inventario["schema"], "public")
        self.assertEqual(inventario["counts"], self.contagens)
        self.assertEqual(inventario["tables"], dict.fromkeys(TABELAS_COMERCIAIS, True))
        self.assertTrue(inventario["table_status"]["clientes"]["row_security_active"])
        self.assertEqual(set(inventario["columns"]), set(TABELAS_CONTAGEM))
        for colunas in inventario["columns"].values():
            for coluna in colunas:
                self.assertEqual(set(coluna), {"name", "type", "nullable", "default"})
        coluna_nome = next(
            c for c in inventario["columns"]["orcamentos"]
            if c["name"] == "cliente_final_nome"
        )
        self.assertEqual(coluna_nome, {
            "name": "cliente_final_nome", "type": "text", "nullable": True, "default": None,
        })
        coluna_id = next(c for c in inventario["columns"]["clientes"] if c["name"] == "id")
        self.assertEqual(coluna_id["default"], "nextval('seq_teste'::regclass)")
        self.assertFalse(coluna_id["nullable"])
        self.assertEqual(inventario["checks"]["orcamentos_numero_duplicate_groups"]["count"], 2)
        self.assertEqual(inventario["checks"]["financeiro_pedidos_orphans"]["count"], 3)
        self.assertTrue(all(
            v["status"] == "checked" and v["missing"] == []
            for v in inventario["checks"].values()
        ))
        self.assertNotIn("DADO_PESSOAL_NAO_DEVE_SAIR", json.dumps(corpo))
        self.assertNotIn("NUMERO_PRIVADO_NAO_DEVE_SAIR", json.dumps(corpo))
        self.provedor.assert_called_once_with()
        comandos = [str(chamada.args[0]) for chamada in self.db.execute.call_args_list]
        self.assertEqual(
            comandos[0], "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
        )
        self.assertIn("SET LOCAL statement_timeout", comandos[1])
        self.assertIn("SET LOCAL lock_timeout", comandos[2])
        self.db.rollback.assert_called_once_with()
        for metodo in ("commit", "add", "add_all", "delete", "flush"):
            getattr(self.db, metodo).assert_not_called()

    def test_confere_exatamente_as_62_colunas_previstas(self):
        _, corpo = self.autorizado()
        fases = corpo["inventory"]["phase1_columns"]
        self.assertEqual(set(fases), set(ESPERADAS))
        self.assertEqual(sum(len(v["expected"]) for v in fases.values()), 62)
        self.assertEqual(
            {t: len(v["expected"]) for t, v in fases.items()},
            {"clientes": 2, "orcamentos": 20, "orcamentos_itens": 1,
             "pedidos": 23, "pedidos_itens": 16},
        )
        for tabela, esperadas in ESPERADAS.items():
            self.assertEqual(fases[tabela]["expected"], esperadas)
            self.assertEqual(fases[tabela]["present"], esperadas)
            self.assertEqual(fases[tabela]["missing"], [])

    def test_colunas_ausentes_sao_listadas_sem_consultas_invalidas(self):
        self.schemas["pedidos"].remove("orcamento_id")
        self.schemas["orcamentos"].remove("cliente_final_nome")
        self.schemas["financeiro"].remove("pedido_id")
        _, corpo = self.autorizado()
        inventario = corpo["inventory"]
        self.assertEqual(
            inventario["phase1_columns"]["orcamentos"]["missing"], ["cliente_final_nome"]
        )
        self.assertEqual(inventario["phase1_columns"]["pedidos"]["missing"], ["orcamento_id"])
        for chave, coluna in [
            ("pedidos_orcamento_duplicate_groups", "pedidos.orcamento_id"),
            ("financeiro_pedidos_orphans", "financeiro.pedido_id"),
        ]:
            check = inventario["checks"][chave]
            self.assertEqual(check["status"], "not_checked")
            self.assertIsNone(check["count"])
            self.assertTrue(any(coluna in nome for nome in check["missing"]))
            self.assertNotIn("'check:" + chave + "'", self.sql_agregados())
        self.assertEqual(inventario["counts"]["pedidos"], 0)

    def test_tabelas_ausentes_nao_sao_confundidas_com_contagem_zero(self):
        self.schemas.pop("financeiro")
        self.schemas.pop("clientes")
        self.schemas.pop("representantes")
        _, corpo = self.autorizado()
        inventario = corpo["inventory"]
        self.assertIsNone(inventario["counts"]["financeiro"])
        self.assertIsNone(inventario["counts"]["clientes"])
        self.assertEqual(inventario["columns"]["financeiro"], [])
        self.assertEqual(
            inventario["table_status"]["financeiro"],
            {"exists": False, "row_security_active": None},
        )
        self.assertFalse(inventario["tables"]["representantes"])
        self.assertEqual(
            inventario["phase1_columns"]["clientes"]["missing"], ESPERADAS["clientes"]
        )
        for chave in ("financeiro_pedidos_orphans", "orcamentos_clientes_orphans"):
            self.assertEqual(inventario["checks"][chave]["status"], "not_checked")
            self.assertIsNone(inventario["checks"][chave]["count"])
        self.assertNotIn("FROM public.financeiro", self.sql_agregados())
        self.assertNotIn("FROM public.clientes", self.sql_agregados())

    def test_catalogo_vazio_nao_executa_consulta_de_agregados(self):
        self.schemas = {}
        _, corpo = self.autorizado()
        inventario = corpo["inventory"]
        self.assertTrue(all(v is None for v in inventario["counts"].values()))
        self.assertTrue(all(not v for v in inventario["tables"].values()))
        self.assertTrue(all(
            v["status"] == "not_checked" and v["count"] is None
            for v in inventario["checks"].values()
        ))
        self.assertFalse(any(
            "'count:" in str(c.args[0]) or "'check:" in str(c.args[0])
            for c in self.db.execute.call_args_list
        ))

    def test_tabela_sem_colunas_existe_mas_verificacoes_ficam_pendentes(self):
        self.schemas["financeiro"] = []
        _, corpo = self.autorizado()
        inventario = corpo["inventory"]
        self.assertTrue(inventario["table_status"]["financeiro"]["exists"])
        self.assertEqual(inventario["columns"]["financeiro"], [])
        self.assertEqual(inventario["counts"]["financeiro"], 0)
        self.assertEqual(inventario["checks"]["financeiro_pedidos_orphans"]["status"], "not_checked")

    def test_consultas_de_integridade_sao_agregadas_e_excluem_fks_nulas(self):
        self.autorizado()
        sql = " ".join(self.sql_agregados().split())
        self.assertIn("UNION ALL", sql)
        self.assertIn("GROUP BY", sql)
        self.assertIn("HAVING count(*) > 1", sql)
        self.assertIn("numero IS NOT NULL", sql)
        self.assertIn("cliente_id IS NOT NULL", sql)
        self.assertIn("orcamento_id IS NOT NULL", sql)
        self.assertIn("pedido_id IS NOT NULL", sql)
        self.assertIn("NOT EXISTS", sql)
        self.assertNotIn("SELECT *", sql.upper())
        for proibido in ("INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "DROP "):
            self.assertNotIn(proibido, sql.upper())

    def test_erros_em_identidade_catalogo_ou_agregados_sao_sanitizados(self):
        segredo = "postgresql://privado:senha-secreta@servidor-interno/banco"
        for etapa in ("identidade", "catalogo", "agregados"):
            with self.subTest(etapa=etapa):
                self.db.reset_mock()
                self.falha_catalogo = None
                self.falha_agregados = None
                self.db.execute.side_effect = self.executar_simulado
                if etapa == "identidade":
                    self.db.execute.side_effect = [Mock(), Mock(), Mock(), SQLAlchemyError(segredo)]
                elif etapa == "catalogo":
                    self.falha_catalogo = SQLAlchemyError(segredo)
                else:
                    self.falha_agregados = SQLAlchemyError(segredo)
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
