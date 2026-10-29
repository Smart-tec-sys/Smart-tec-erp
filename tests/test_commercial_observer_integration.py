"""Integracao 4C.14: o observador comercial no app FastAPI, somente em modo OFF.

Sem banco real, sem rede e sem migrations. O app e importado em subprocesso com
ambiente ficticio (URL invalida; o engine principal nao conecta ao ser criado).
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from app import settings
from app.tenant import commercial_access as acesso
from app.tenant import commercial_observer_integration as integ

RAIZ = Path(__file__).resolve().parents[1]

SONDA = r'''
import json, sys, threading
import sqlalchemy
import sqlalchemy.engine
from concurrent.futures import ThreadPoolExecutor

engines = []
orig = sqlalchemy.create_engine
def contar(*a, **k):
    engines.append(1)
    return orig(*a, **k)
sqlalchemy.create_engine = contar
sqlalchemy.engine.create_engine = contar
def proibido(*a, **k):
    raise AssertionError("thread de observacao")
ThreadPoolExecutor.submit = proibido
import app.settings as s
s.PROJECT_ROOT = __import__("pathlib").Path(sys.argv[1])
threads_antes = {t.name for t in threading.enumerate()}
import app.main as m
import asyncio
rotas_antes = sorted(r.path for r in m.app.routes)
saida = {}

async def pedir(app, caminho):
    msgs = []
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    async def send(msg):
        msgs.append(msg)
    escopo = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
              "scheme": "http", "path": caminho, "raw_path": caminho.encode(), "query_string": b"",
              "headers": [(b"host", b"testserver")], "client": ("127.0.0.1", 1), "server": ("testserver", 80)}
    await app(escopo, receive, send)
    status = next(x["status"] for x in msgs if x["type"] == "http.response.start")
    corpo = b"".join(x.get("body", b"") for x in msgs if x["type"] == "http.response.body")
    return [status, json.loads(corpo) if corpo else None]

async def ciclo(app):
    entrada, saida_l = asyncio.Queue(), asyncio.Queue()
    tarefa = asyncio.ensure_future(app({"type": "lifespan", "asgi": {"version": "3.0"}}, entrada.get, saida_l.put))
    await entrada.put({"type": "lifespan.startup"})
    saida["startup"] = (await saida_l.get())["type"]
    saida["health"] = await pedir(app, "/health")
    saida["raiz"] = await pedir(app, "/")
    saida["inexistente"] = (await pedir(app, "/rota-inexistente-4c14"))[0]
    saida["admin_sem_auth"] = (await pedir(app, "/admin/assinaturas"))[0]
    saida["threads_extras"] = sorted({t.name for t in threading.enumerate()} - threads_antes)
    await entrada.put({"type": "lifespan.shutdown"})
    saida["shutdown"] = (await saida_l.get())["type"]
    await tarefa

asyncio.run(ciclo(m.app))
saida["engines"] = len(engines)
saida["pool_importado"] = "app.tenant.commercial_observer_pool" in sys.modules
saida["modo"] = m.app.state.integracao_comercial.modo.value
saida["possui_recursos"] = m.app.state.integracao_comercial.possui_recursos
saida["ativo"] = m.app.state.integracao_comercial.observador.ativo
saida["rotas"] = len(rotas_antes)
saida["rotas_iguais"] = rotas_antes == sorted(r.path for r in m.app.routes)
print("JSON:" + json.dumps(saida))
'''


def executar_app(modo=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SMARTTEC_", "DATABASE", "DB_", "SUPABASE_"))}
    env.update({"DATABASE_URL": "postgresql+psycopg2://u:p@host-inexistente.invalid:5432/d",
                "SMARTTEC_AUTH_MODE": "dev", "PYTHONPATH": str(RAIZ)})
    if modo is not None:
        env["SMARTTEC_COMMERCIAL_MODE"] = modo
    r = subprocess.run([sys.executable, "-c", SONDA, str(RAIZ / "tests")], cwd=RAIZ, env=env,
                       capture_output=True, text=True, timeout=120)
    linha = [x for x in r.stdout.splitlines() if x.startswith("JSON:")]
    if not linha:
        if "No module named" in r.stderr:
            raise unittest.SkipTest("dependencia do app ausente neste Python: " + r.stderr.strip().splitlines()[-1])
        raise AssertionError(f"sonda falhou: {r.stderr[-800:]}")
    return json.loads(linha[0][5:])


class ConfiguracaoTest(unittest.TestCase):
    def test_ausencia_resulta_em_off(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("SMARTTEC_COMMERCIAL_MODE", None)
            self.assertEqual(settings.get_commercial_mode_setting(), "off")
        i = integ.preparar_integracao_comercial(None)
        self.assertIs(i.modo, acesso.ModoComercial.OFF)

    def test_valores_invalidos_resultam_em_off(self):
        for v in ("", "  ", "ligado", "true", "1", "OBSERVE;", 5, [], {}, b"observe", object()):
            with self.subTest(v=v):
                i = integ.preparar_integracao_comercial(v)
                self.assertIs(i.modo, acesso.ModoComercial.OFF)
                self.assertFalse(i.observador.ativo)
                self.assertFalse(i.modo_solicitado_valido)

    def test_observe_e_enforce_solicitados_continuam_off(self):
        for v in ("observe", "OBSERVE", " Enforce ", "enforce"):
            with self.subTest(v=v):
                i = integ.preparar_integracao_comercial(v)
                self.assertIs(i.modo, acesso.ModoComercial.OFF)
                self.assertFalse(i.observador.ativo)
                self.assertFalse(i.possui_recursos)
                self.assertEqual(i.observador.config.empresas_piloto, frozenset())

    def test_enforce_indisponivel_na_configuracao_base(self):
        c = acesso.carregar_configuracao("enforce", (1,))
        self.assertIs(c.modo, acesso.ModoComercial.OFF)
        self.assertTrue(c.enforce_solicitado)
        self.assertEqual(integ.MODOS_HABILITADOS, frozenset({acesso.ModoComercial.OFF}))

    def test_off_nao_observa_nem_consulta(self):
        i = integ.preparar_integracao_comercial("observe")
        chamadas = []
        r = i.observador.observar(mock.Mock(), 5)
        self.assertEqual(chamadas, [])
        self.assertFalse(r.observado)
        self.assertFalse(r.bloqueia)
        self.assertIsNone(r.decisao)
        self.assertIsNone(i.encerrar())

    def test_off_nao_cria_pool_nem_engine_nem_thread(self):
        import threading
        antes = threading.active_count()
        with mock.patch("sqlalchemy.create_engine") as engine, \
                mock.patch("concurrent.futures.ThreadPoolExecutor") as executor, \
                self.assertNoLogs("smarttec.commercial_access", level="DEBUG"):
            integ.preparar_integracao_comercial("observe").observador.observar(mock.Mock(), 5)
        engine.assert_not_called()
        executor.assert_not_called()
        self.assertEqual(threading.active_count(), antes)

    def test_fonte_sem_ambiente_banco_ou_rotas(self):
        fonte = Path(integ.__file__).read_text(encoding="utf-8")
        for proibido in ("os." + "environ", "get" + "env", "create_" + "engine", "commercial_observer_pool",
                         "fastapi", "Depends", "app.database", "SessionLocal"):
            self.assertNotIn(proibido, fonte)


class AplicacaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sem_config = executar_app()
        cls.invalido = executar_app("xpto")
        cls.observe = executar_app("observe")
        cls.enforce = executar_app("enforce")

    def test_modo_off_em_todas_as_configuracoes(self):
        for r in (self.sem_config, self.invalido, self.observe, self.enforce):
            self.assertEqual(r["modo"], "off")
            self.assertFalse(r["ativo"])
            self.assertFalse(r["possui_recursos"])

    def test_off_nao_cria_pool_engine_adicional_nem_thread(self):
        for r in (self.sem_config, self.invalido, self.observe, self.enforce):
            self.assertEqual(r["engines"], 1)  # somente o engine principal do ERP
            self.assertFalse(r["pool_importado"])
            # Threads do AnyIO servem as rotas sincronas; nenhuma e de observacao.
            self.assertEqual([n for n in r["threads_extras"] if "observe" in n.lower() or "commercial" in n.lower()], [])

    def test_inicializacao_encerramento_e_respostas_preservadas(self):
        for r in (self.sem_config, self.invalido, self.observe, self.enforce):
            self.assertEqual(r["health"], [200, {"status": "ok", "service": "smart-tec-erp-api"}])
            self.assertEqual(r["raiz"], [200, {"mensagem": "API do Smart-tec ERP rodando perfeitamente!"}])
            self.assertEqual(r["inexistente"], 404)
            self.assertTrue(r["rotas_iguais"])
            self.assertEqual((r["startup"], r["shutdown"]), ("lifespan.startup.complete", "lifespan.shutdown.complete"))
        self.assertEqual(self.sem_config["admin_sem_auth"], self.observe["admin_sem_auth"])
        self.assertIn(self.sem_config["admin_sem_auth"], (401, 403, 404))

    def test_respostas_identicas_entre_modos(self):
        chaves = ("health", "raiz", "inexistente", "admin_sem_auth", "rotas")
        for r in (self.invalido, self.observe, self.enforce):
            self.assertEqual({k: r[k] for k in chaves}, {k: self.sem_config[k] for k in chaves})

    def test_autenticacao_nao_referencia_a_integracao(self):
        for arq in ("app/auth/dependencies.py", "app/auth/supabase_jwt.py", "app/tenant/dependencies.py"):
            texto = (RAIZ / arq).read_text(encoding="utf-8")
            self.assertNotIn("commercial_observer", texto)
            self.assertNotIn("integracao_comercial", texto)

    def test_nenhum_router_usa_o_observador(self):
        for arq in (RAIZ / "app" / "routes").glob("*.py"):
            texto = arq.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("commercial_observer", texto)
            self.assertNotIn("integracao_comercial", texto)


if __name__ == "__main__":
    unittest.main()
