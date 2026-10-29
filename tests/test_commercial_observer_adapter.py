import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.dialects import postgresql

from app.tenant import commercial_access as acesso
from app.tenant import commercial_evidence as ev
from app.tenant import commercial_observer_adapter as adp
from app.tenant.context import LEGACY_UNSCOPED, TenantContext, TenantOrigin

SP = ZoneInfo("America/Sao_Paulo")
CONV = ev.ConvencaoTemporal(fuso_comercial=SP, fuso_timestamps_sem_fuso=SP)


class _Resultado:
    def __init__(self, linhas=()):
        self.linhas = linhas

    def mappings(self):
        return self

    def all(self):
        return list(self.linhas)


class SessaoFalsa:
    def __init__(self, erro_em=None):
        self.chamadas = []
        self.rollbacks = 0
        self.fechada = False
        self.erro_em = erro_em

    def execute(self, statement, params=None):
        self.chamadas.append((str(statement), dict(params or {})))
        if self.erro_em is not None and len(self.chamadas) == self.erro_em:
            raise RuntimeError("falha com senha=abc")
        return _Resultado()

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.fechada = True


class FabricaFalsa:
    def __init__(self, **kw):
        self.sessoes = []
        self.kw = kw

    def __call__(self):
        s = SessaoFalsa(**self.kw)
        self.sessoes.append(s)
        return s


def tenant(empresa=1, user=10):
    return TenantContext(empresa, user)


def observador(modo="observe", piloto=(1,), fabrica=None, **kw):
    fabrica = fabrica if fabrica is not None else FabricaFalsa()
    kw.setdefault("convencao", CONV)
    return adp.criar_observador(modo, piloto, session_factory=fabrica, **kw), fabrica


class ConfiguracaoTest(unittest.TestCase):
    def test_padrao_e_off_e_nao_cria_sessao(self):
        for obs, fab in (observador(None), observador("off"), observador("enforce"),
                         observador("ligado"), observador("observe", "x,y"),
                         observador("observe", (1,), timeout_leitura_s=0)):
            self.assertFalse(obs.ativo)
            self.assertIs(obs.config.modo, acesso.ModoComercial.OFF)
            r = obs.observar(tenant(), 5)
            self.assertFalse(r.observado)
            self.assertFalse(r.bloqueia)
            self.assertEqual(fab.sessoes, [])

    def test_criar_observador_sem_argumentos_e_off(self):
        obs = adp.criar_observador()
        self.assertFalse(obs.ativo)
        self.assertFalse(obs.observar(tenant(), 5).observado)

    def test_observe_sem_fabrica_valida_vira_off(self):
        for fabrica in (None, "nao-chamavel", 5):
            obs = adp.criar_observador("observe", (1,), session_factory=fabrica, convencao=CONV)
            self.assertFalse(obs.ativo)
            self.assertIs(obs.config.modo, acesso.ModoComercial.OFF)

    def test_enforce_indisponivel(self):
        obs, fab = observador("enforce")
        self.assertTrue(obs.config.enforce_solicitado)
        self.assertFalse(obs.ativo)
        self.assertEqual(fab.sessoes, [])

    def test_observe_valido_fica_ativo(self):
        obs, _ = observador()
        self.assertTrue(obs.ativo)
        self.assertEqual(obs.config.empresas_piloto, frozenset({1}))


class ObservacaoTest(unittest.TestCase):
    def test_fora_do_piloto_nao_abre_sessao(self):
        obs, fab = observador(piloto=(2,))
        r = obs.observar(tenant(1), 5)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.NAO_OBSERVADO_NAO_PILOTO)
        self.assertEqual(fab.sessoes, [])

    def test_contextos_nao_autenticados_nao_abrem_sessao(self):
        obs, fab = observador()
        for ctx in (LEGACY_UNSCOPED, TenantContext(1, 10, TenantOrigin.SESSION),
                    TenantContext(1, 10, TenantOrigin.EXPLICIT_TEST), TenantContext(1, None),
                    None, {"empresa_id": 1}, "1", 1):
            r = obs.observar(ctx, 5)
            self.assertIs(r.situacao, acesso.SituacaoObservacao.CONTEXTO_INVALIDO, ctx)
        self.assertEqual(fab.sessoes, [])

    def test_empresa_da_consulta_vem_do_contexto(self):
        obs, fab = observador(piloto=(1, 2))
        obs.observar(tenant(2), 9)
        consulta = fab.sessoes[0].chamadas[-1]
        self.assertEqual(consulta[1], {"empresa_id": 2})

    def test_uma_sessao_e_uma_consulta_de_evidencias_por_observacao(self):
        obs, fab = observador()
        r = obs.observar(tenant(), 5)
        self.assertEqual(len(fab.sessoes), 1)
        evid = [c for c in fab.sessoes[0].chamadas if "set_config" not in c[0]]
        self.assertEqual(len(evid), 1)
        self.assertTrue(r.observado)
        self.assertFalse(r.decisao.permitido)
        self.assertFalse(r.bloqueia)

    def test_sessao_encerrada_com_rollback(self):
        obs, fab = observador()
        obs.observar(tenant(), 5)
        s = fab.sessoes[0]
        self.assertTrue(s.fechada)
        self.assertGreaterEqual(s.rollbacks, 1)

    def test_sem_convencao_nao_abre_sessao(self):
        obs = adp.criar_observador("observe", (1,), session_factory=FabricaFalsa())
        fab = obs._fabrica
        r = obs.observar(tenant(), 5)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE)
        self.assertFalse(r.bloqueia)


class TransacaoSomenteLeituraTest(unittest.TestCase):
    def test_preparo_antes_da_consulta_e_local_a_transacao(self):
        obs, fab = observador(timeout_leitura_s=2.0)
        obs.observar(tenant(), 5)
        chamadas = fab.sessoes[0].chamadas
        preparo = chamadas[:4]
        self.assertTrue(all("set_config" in c[0] and "true)" in c[0] for c in preparo))
        self.assertEqual(
            [c[1]["nome"] for c in preparo],
            ["transaction_read_only", "statement_timeout", "lock_timeout",
             "idle_in_transaction_session_timeout"],
        )
        self.assertEqual(preparo[0][1]["valor"], "on")
        self.assertEqual({c[1]["valor"] for c in preparo[1:]}, {"1600"})
        self.assertIn("empresas", chamadas[4][0])

    def test_preparo_ocorre_uma_vez_por_sessao(self):
        sessao = SessaoFalsa()
        s = adp.SessaoObservacao(sessao, 100)
        s.execute("a", {})
        s.execute("b", {})
        self.assertEqual(sum("set_config" in c[0] for c in sessao.chamadas), 4)
        self.assertEqual(len(sessao.chamadas), 6)

    def test_sql_de_preparo_compila_para_postgresql_sem_set_global(self):
        sql = str(adp._SQL_PREPARO.compile(dialect=postgresql.dialect())).lower()
        self.assertIn("set_config", sql)
        self.assertTrue(sql.rstrip().endswith("true)"))
        for proibido in ("alter ", "set session", "set statement_timeout", "reset all"):
            self.assertNotIn(proibido, sql)

    def test_timeout_do_banco_e_menor_que_a_espera(self):
        for s in (0.05, 0.1, 1, 2, 10):
            self.assertLess(adp.timeout_banco_ms(s), s * 1000 + 1)
            self.assertGreaterEqual(adp.timeout_banco_ms(s), adp.TIMEOUT_BANCO_MIN_MS)
        self.assertLess(adp.timeout_banco_ms(2.0), 2000)

    def test_valores_de_timeout_usam_parametros_nao_concatenacao(self):
        obs, fab = observador(timeout_leitura_s=1.0)
        obs.observar(tenant(), 5)
        for sql, params in fab.sessoes[0].chamadas[:4]:
            self.assertNotIn("800", sql)
            self.assertIn("valor", params)


class FalhasTest(unittest.TestCase):
    def test_falha_no_preparo_nao_derruba_nem_consulta(self):
        obs, fab = observador(fabrica=FabricaFalsa(erro_em=2))
        r = obs.observar(tenant(), 5)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.AVALIADO)
        self.assertFalse(r.decisao.permitido)
        self.assertFalse(r.bloqueia)
        s = fab.sessoes[0]
        self.assertTrue(s.fechada)
        self.assertEqual(sum("empresas" in c[0] for c in s.chamadas), 0)

    def test_falha_ao_criar_sessao_nao_derruba(self):
        def quebrada():
            raise ConnectionError("indisponivel")

        obs = adp.criar_observador("observe", (1,), session_factory=quebrada, convencao=CONV)
        r = obs.observar(tenant(), 5)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_LEITURA)
        self.assertFalse(r.bloqueia)

    def test_falha_de_rollback_ou_close_nao_derruba(self):
        class Ruim(SessaoFalsa):
            def rollback(self):
                raise RuntimeError

            def close(self):
                raise RuntimeError

        obs = adp.criar_observador("observe", (1,), session_factory=Ruim, convencao=CONV)
        self.assertTrue(obs.observar(tenant(), 5).observado)

    def test_observar_nunca_propaga(self):
        obs, _ = observador()
        original = acesso.observar_acesso
        acesso.observar_acesso = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        try:
            r = obs.observar(tenant(), 5)
        finally:
            acesso.observar_acesso = original
        self.assertFalse(r.bloqueia)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_POLITICA)

    def test_timeout_efetivo_da_espera_continua_valendo(self):
        import threading
        import time

        liberar = threading.Event()

        class Lenta(SessaoFalsa):
            def execute(self, statement, params=None):
                if "set_config" not in str(statement):
                    liberar.wait(5)
                return super().execute(statement, params)

        obs = adp.criar_observador("observe", (1,), session_factory=Lenta, convencao=CONV,
                                   timeout_leitura_s=0.1)
        inicio = time.monotonic()
        try:
            r = obs.observar(tenant(), 5)
        finally:
            liberar.set()
        self.assertLess(time.monotonic() - inicio, 2)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.TIMEOUT_LEITURA)
        self.assertFalse(r.bloqueia)


class IsolamentoEEscopoTest(unittest.TestCase):
    def test_empresas_nao_compartilham_sessao(self):
        obs, fab = observador(piloto=(1, 2))
        obs.observar(tenant(1), 5)
        obs.observar(tenant(2), 5)
        self.assertEqual(len(fab.sessoes), 2)
        self.assertIsNot(fab.sessoes[0], fab.sessoes[1])
        self.assertEqual(fab.sessoes[0].chamadas[-1][1], {"empresa_id": 1})
        self.assertEqual(fab.sessoes[1].chamadas[-1][1], {"empresa_id": 2})

    def test_logs_sem_dados_sensiveis(self):
        obs, _ = observador(piloto=(777777,), fabrica=FabricaFalsa(erro_em=2), segredo_identificador=b"segredo-de-teste-0123456789")
        with self.assertLogs("smarttec.commercial_access", "DEBUG") as capturado:
            obs.observar(tenant(777777, 888888), 42)
        texto = "\n".join(capturado.output)
        for proibido in ("777777", "888888", "senha", "abc", "segredo-de-teste", "SELECT"):
            self.assertNotIn(proibido, texto)

    def test_modulo_nao_acessa_ambiente_nem_registra_rotas(self):
        fonte = (Path(__file__).resolve().parents[1] / "app" / "tenant"
                 / "commercial_observer_adapter.py").read_text(encoding="utf-8")
        for proibido in ("os.environ", "getenv", "app.database", "app.settings", "fastapi",
                         "APIRouter", "Depends", "create_engine", "INSERT", "UPDATE ", "DELETE ",
                         "commit(", "ALTER "):
            self.assertNotIn(proibido, fonte, proibido)

    def test_adaptador_nao_decide_autorizacao(self):
        fonte = (Path(__file__).resolve().parents[1] / "app" / "tenant"
                 / "commercial_observer_adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("avaliar_acesso_comercial", fonte)
        self.assertNotIn("HTTPException", fonte)


if __name__ == "__main__":
    unittest.main()
