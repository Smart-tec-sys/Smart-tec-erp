import threading
import time
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.tenant import commercial_access as acesso
from app.tenant import commercial_evidence as ev
from app.tenant import commercial_policy as pol
from app.tenant.context import LEGACY_UNSCOPED, TenantContext, TenantOrigin

UTC = timezone.utc
SP = ZoneInfo("America/Sao_Paulo")
AGORA = datetime(2024, 5, 10, 15, tzinfo=UTC)
CONV = ev.ConvencaoTemporal(fuso_comercial=SP, fuso_timestamps_sem_fuso=SP)
SEGREDO = b"segredo-de-teste-0123456789"


def tenant(empresa=1, user=10):
    return TenantContext(empresa, user)


def relogio():
    return AGORA


class Sessao:
    def __init__(self):
        self.fechada = False
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.fechada = True


class Fabrica:
    def __init__(self):
        self.criadas = []

    def __call__(self):
        s = Sessao()
        self.criadas.append(s)
        return s


class Leitor:
    def __init__(self, resultado=None, erro=None, espera=0.0):
        self.chamadas = []
        self.resultado = resultado or ev.ResultadoLeitura(pol.EvidenciasComerciais())
        self.erro = erro
        self.espera = espera

    def __call__(self, sessao, contexto, *, agora, convencao):
        self.chamadas.append((contexto, agora, convencao))
        if self.espera:
            time.sleep(self.espera)
        if self.erro:
            raise self.erro
        return self.resultado


def cfg(modo="observe", piloto=(1,), **kw):
    kw.setdefault("convencao", CONV)
    return acesso.carregar_configuracao(modo, piloto, **kw)


_PADRAO = object()


def observar(config, ctx=_PADRAO, modulo=5, fabrica=None, **kw):
    fabrica = fabrica or Fabrica()
    kw.setdefault("relogio", relogio)
    return acesso.observar_acesso(config, tenant() if ctx is _PADRAO else ctx, modulo, sessao_factory=fabrica, **kw), fabrica


class ModosTest(unittest.TestCase):
    def test_padrao_e_off(self):
        self.assertIs(acesso.ConfiguracaoObservacao().modo, acesso.ModoComercial.OFF)
        self.assertIs(acesso.carregar_configuracao().modo, acesso.ModoComercial.OFF)

    def test_off_nao_consulta_nem_avalia_nem_registra(self):
        leitor, avaliador = Leitor(), lambda *a: self.fail("nao deve avaliar")
        with self.assertNoLogs("smarttec.commercial_access"):
            r, f = observar(cfg("off"), leitor=leitor, avaliador=avaliador)
            r2, f2 = observar(acesso.ConfiguracaoObservacao(), leitor=leitor)
        self.assertEqual((leitor.chamadas, f.criadas, f2.criadas), ([], [], []))
        self.assertFalse(r.observado)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.NAO_OBSERVADO_MODO)
        self.assertFalse(r2.observado)

    def test_observe_avalia_sem_bloquear(self):
        leitor = Leitor()
        r, f = observar(cfg(), leitor=leitor)
        self.assertTrue(r.observado)
        self.assertFalse(r.bloqueia)
        self.assertEqual(len(leitor.chamadas), 1)
        self.assertEqual(len(f.criadas), 1)
        self.assertTrue(f.criadas[0].fechada)
        self.assertGreaterEqual(f.criadas[0].rollbacks, 1)

    def test_decisao_negativa_registrada_sem_alterar_resposta(self):
        with self.assertLogs("smarttec.commercial_access", "INFO") as capturado:
            r, _ = observar(cfg(), leitor=Leitor())
        self.assertIs(r.situacao, acesso.SituacaoObservacao.AVALIADO)
        self.assertFalse(r.decisao.permitido)
        self.assertIs(r.decisao.motivo, pol.MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
        self.assertFalse(r.bloqueia)
        self.assertIn("EVIDENCIAS_INCOMPLETAS", capturado.output[0])
        self.assertIn("permitido=false", capturado.output[0])

    def test_enforce_nao_e_ativavel(self):
        for valor in ("enforce", "ENFORCE", " Enforce "):
            c = acesso.carregar_configuracao(valor, (1,), convencao=CONV)
            self.assertIs(c.modo, acesso.ModoComercial.OFF)
            self.assertTrue(c.enforce_solicitado)
            self.assertEqual(c.erros, ("ENFORCE_INDISPONIVEL",))
        leitor = Leitor()
        # Mesmo construido diretamente, enforce nao avalia nem bloqueia.
        direto = acesso.ConfiguracaoObservacao(modo=acesso.ModoComercial.ENFORCE, empresas_piloto=frozenset({1}), convencao=CONV)
        r, f = observar(direto, leitor=leitor)
        self.assertFalse(r.observado)
        self.assertFalse(r.bloqueia)
        self.assertEqual((leitor.chamadas, f.criadas), ([], []))

    def test_resultado_nunca_bloqueia(self):
        self.assertFalse(acesso.ResultadoObservacao(True, acesso.SituacaoObservacao.AVALIADO,
                                                    pol.DecisaoAcesso(False, pol.MotivoAcesso.ASSINATURA_AUSENTE)).bloqueia)


class ConfiguracaoTest(unittest.TestCase):
    def test_valores_invalidos_resultam_em_off(self):
        casos = [
            dict(modo="ligado"), dict(modo=True), dict(modo=1), dict(modo=""),
            dict(modo="observe", empresas_piloto="a,b"), dict(modo="observe", empresas_piloto=[0]),
            dict(modo="observe", empresas_piloto=[True]), dict(modo="observe", empresas_piloto=[-1]),
            dict(modo="observe", empresas_piloto=[1.5]), dict(modo="observe", empresas_piloto=7),
            dict(modo="observe", empresas_piloto=list(range(1, 100))),
            dict(modo="observe", empresas_piloto=[1], timeout_leitura_s=0),
            dict(modo="observe", empresas_piloto=[1], timeout_leitura_s=999),
            dict(modo="observe", empresas_piloto=[1], timeout_leitura_s=float("nan")),
            dict(modo="observe", empresas_piloto=[1], timeout_leitura_s="2"),
            dict(modo="observe", empresas_piloto=[1], segredo_identificador=b"curto"),
            dict(modo="observe", empresas_piloto=[1], convencao="SP"),
        ]
        for caso in casos:
            c = acesso.carregar_configuracao(**caso)
            self.assertIs(c.modo, acesso.ModoComercial.OFF, caso)
            self.assertFalse(c.empresas_piloto, caso)
            r, f = observar(c)
            self.assertFalse(r.observado, caso)
            self.assertEqual(f.criadas, [], caso)

    def test_piloto_como_texto_e_colecoes(self):
        self.assertEqual(acesso.carregar_configuracao("observe", "3, 4,5").empresas_piloto, frozenset({3, 4, 5}))
        self.assertEqual(acesso.carregar_configuracao("observe", [7, 8]).empresas_piloto, frozenset({7, 8}))
        self.assertEqual(acesso.carregar_configuracao("observe").empresas_piloto, frozenset())

    def test_segredo_nao_aparece_no_repr(self):
        self.assertNotIn("segredo-de-teste", repr(cfg(segredo_identificador=SEGREDO)))

    def test_config_com_tipo_errado_e_ignorada(self):
        for c in (None, {"modo": "observe"}, "observe"):
            r, f = observar(c)
            self.assertFalse(r.observado)
            self.assertEqual(f.criadas, [])


class PilotoEIsolamentoTest(unittest.TestCase):
    def test_empresa_fora_do_piloto_nao_e_observada(self):
        leitor = Leitor()
        r, f = observar(cfg(piloto=(2,)), ctx=tenant(1), leitor=leitor)
        self.assertFalse(r.observado)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.NAO_OBSERVADO_NAO_PILOTO)
        self.assertEqual((leitor.chamadas, f.criadas), ([], []))

    def test_piloto_vazio_nao_observa_ninguem(self):
        leitor = Leitor()
        r, _ = observar(cfg(piloto=()), leitor=leitor)
        self.assertFalse(r.observado)
        self.assertEqual(leitor.chamadas, [])

    def test_empresa_vem_somente_do_contexto_autenticado(self):
        leitor = Leitor()
        observar(cfg(piloto=(1, 2)), ctx=tenant(2), modulo=9, leitor=leitor)
        contexto, agora, convencao = leitor.chamadas[0]
        self.assertEqual(contexto.empresa_id, 2)
        self.assertIs(convencao, CONV)
        self.assertEqual(agora, AGORA)

    def test_avaliacao_usa_empresa_e_modulo_da_consulta(self):
        vistos = []

        def avaliador(consulta, evidencias):
            vistos.append(consulta)
            return pol.DecisaoAcesso(False, pol.MotivoAcesso.ASSINATURA_AUSENTE)

        observar(cfg(piloto=(1, 2)), ctx=tenant(2), modulo=9, leitor=Leitor(), avaliador=avaliador)
        self.assertEqual(vistos, [pol.ConsultaAcesso(2, 9, AGORA)])

    def test_contextos_nao_autenticados_sao_rejeitados(self):
        invalidos = [
            LEGACY_UNSCOPED,
            TenantContext(1, 10, TenantOrigin.SESSION),
            TenantContext(1, 10, TenantOrigin.EXPLICIT_TEST),
            TenantContext(1, None),
            TenantContext(1, "abc"),
            None,
            {"empresa_id": 1},
            1,
        ]
        for ctx in invalidos:
            leitor = Leitor()
            r, f = observar(cfg(), ctx=ctx, leitor=leitor)
            self.assertFalse(r.observado, ctx)
            self.assertIs(r.situacao, acesso.SituacaoObservacao.CONTEXTO_INVALIDO, ctx)
            self.assertEqual((leitor.chamadas, f.criadas), ([], []), ctx)

    def test_modulo_invalido_e_rejeitado(self):
        for modulo in (0, -1, None, "5", True, 2.0):
            leitor = Leitor()
            r, _ = observar(cfg(), modulo=modulo, leitor=leitor)
            self.assertIs(r.situacao, acesso.SituacaoObservacao.CONTEXTO_INVALIDO, modulo)
            self.assertEqual(leitor.chamadas, [])

    def test_fabrica_invalida(self):
        r = acesso.observar_acesso(cfg(), tenant(), 5, sessao_factory=None, relogio=relogio)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.CONTEXTO_INVALIDO)

    def test_empresas_diferentes_nao_compartilham_leitura(self):
        leitor = Leitor()
        fabrica = Fabrica()
        for empresa in (1, 2):
            observar(cfg(piloto=(1, 2)), ctx=tenant(empresa), fabrica=fabrica, leitor=leitor)
        self.assertEqual([c[0].empresa_id for c in leitor.chamadas], [1, 2])
        self.assertEqual(len(fabrica.criadas), 2)
        self.assertTrue(all(s.fechada for s in fabrica.criadas))


class FalhasTest(unittest.TestCase):
    def test_erro_de_banco_no_leitor_nao_derruba(self):
        r, f = observar(cfg(), leitor=Leitor(erro=RuntimeError("senha=segredo host=db")))
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_LEITURA)
        self.assertIsNone(r.decisao)
        self.assertFalse(r.bloqueia)
        self.assertTrue(f.criadas[0].fechada)

    def test_erro_ao_criar_sessao_nao_derruba(self):
        def fabrica():
            raise ConnectionError("db indisponivel")

        r = acesso.observar_acesso(cfg(), tenant(), 5, sessao_factory=fabrica, relogio=relogio, leitor=Leitor())
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_LEITURA)
        self.assertFalse(r.bloqueia)

    def test_leitor_real_com_sessao_que_falha_vira_decisao_negativa(self):
        class Quebrada(Sessao):
            def execute(self, *a, **k):
                raise RuntimeError("falha interna")

        r = acesso.observar_acesso(cfg(), tenant(), 5, sessao_factory=Quebrada, relogio=relogio)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.AVALIADO)
        self.assertFalse(r.decisao.permitido)
        self.assertIn("FALHA_CONSULTA", r.limitacoes)

    def test_falha_na_politica_nao_bloqueia(self):
        def avaliador(*a):
            raise RuntimeError("bug")

        r, _ = observar(cfg(), leitor=Leitor(), avaliador=avaliador)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_POLITICA)
        self.assertIsNone(r.decisao)
        self.assertFalse(r.bloqueia)

    def test_politica_com_retorno_invalido(self):
        r, _ = observar(cfg(), leitor=Leitor(), avaliador=lambda *a: True)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_POLITICA)
        self.assertIsNone(r.decisao)

    def test_leitura_com_formato_inesperado(self):
        r, _ = observar(cfg(), leitor=Leitor(resultado=object()))
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_POLITICA)

    def test_relogio_com_falha_nao_derruba(self):
        def relogio_ruim():
            raise RuntimeError

        r = acesso.observar_acesso(cfg(), tenant(), 5, sessao_factory=Fabrica(), relogio=relogio_ruim, leitor=Leitor())
        self.assertIs(r.situacao, acesso.SituacaoObservacao.FALHA_POLITICA)
        self.assertFalse(r.bloqueia)

    def test_timeout_tratado_com_seguranca(self):
        liberar = threading.Event()

        class Lento(Leitor):
            def __call__(self, *a, **k):
                liberar.wait(5)
                return super().__call__(*a, **k)

        config = cfg(timeout_leitura_s=0.1)
        inicio = time.monotonic()
        try:
            r, _ = observar(config, leitor=Lento())
        finally:
            liberar.set()
        self.assertLess(time.monotonic() - inicio, 2)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.TIMEOUT_LEITURA)
        self.assertIsNone(r.decisao)
        self.assertFalse(r.bloqueia)

    def test_excecoes_de_sistema_nao_sao_engolidas_como_autorizacao(self):
        for erro in (ValueError("x"), KeyError("y"), TypeError("z")):
            r, _ = observar(cfg(), leitor=Leitor(erro=erro))
            self.assertFalse(r.bloqueia)
            self.assertIsNone(r.decisao)


class ConvencaoTemporalTest(unittest.TestCase):
    def test_sem_convencao_comercial_nao_le_e_registra_evidencia_insuficiente(self):
        leitor = Leitor()
        r, f = observar(acesso.carregar_configuracao("observe", (1,)), leitor=leitor)
        self.assertIs(r.situacao, acesso.SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE)
        self.assertIsNone(r.decisao)
        self.assertIn("CONVENCAO_TEMPORAL_AUSENTE", r.limitacoes)
        self.assertEqual((leitor.chamadas, f.criadas), ([], []))
        self.assertFalse(r.bloqueia)

    def test_limitacao_temporal_do_leitor_e_registrada_e_nega(self):
        leitura = ev.ResultadoLeitura(pol.EvidenciasComerciais(), (ev.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE,))
        r, _ = observar(cfg(), leitor=Leitor(resultado=leitura))
        self.assertIs(r.situacao, acesso.SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE)
        self.assertFalse(r.decisao.permitido)
        self.assertFalse(r.bloqueia)

    def test_data_ambigua_tambem_e_temporal(self):
        leitura = ev.ResultadoLeitura(pol.EvidenciasComerciais(), (ev.MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA,))
        r, _ = observar(cfg(), leitor=Leitor(resultado=leitura))
        self.assertIs(r.situacao, acesso.SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE)
        self.assertFalse(r.decisao.permitido)

    def test_ausencia_de_evidencia_nunca_vira_autorizacao(self):
        for limitacao in ev.MotivoLeitura:
            leitura = ev.ResultadoLeitura(pol.EvidenciasComerciais(), (limitacao,))
            r, _ = observar(cfg(), leitor=Leitor(resultado=leitura))
            self.assertFalse(r.decisao.permitido, limitacao)

    def test_nenhum_fuso_e_presumido(self):
        leitor = Leitor()
        observar(cfg(), leitor=leitor)
        convencao = leitor.chamadas[0][2]
        self.assertIs(convencao, CONV)
        self.assertEqual(ev.ConvencaoTemporal().fuso_timestamps_sem_fuso, None)
        parcial = ev.ConvencaoTemporal(fuso_comercial=SP)
        c = acesso.carregar_configuracao("observe", (1,), convencao=parcial)
        observar(c, leitor=leitor)
        self.assertIsNone(leitor.chamadas[1][2].fuso_timestamps_sem_fuso)


class LeituraUnicaTest(unittest.TestCase):
    def test_uma_leitura_por_avaliacao(self):
        leitor, avaliador_chamadas = Leitor(), []

        def avaliador(consulta, evidencias):
            avaliador_chamadas.append(1)
            return pol.DecisaoAcesso(False, pol.MotivoAcesso.ASSINATURA_AUSENTE)

        r, f = observar(cfg(), leitor=leitor, avaliador=avaliador)
        self.assertEqual((len(leitor.chamadas), len(avaliador_chamadas), len(f.criadas)), (1, 1, 1))
        for _ in range(3):
            observar(cfg(), leitor=leitor, avaliador=avaliador)
        self.assertEqual(len(leitor.chamadas), 4)

    def test_leitor_real_executa_uma_unica_consulta(self):
        execucoes = []

        class Resultado:
            def mappings(self):
                return self

            def all(self):
                return []

        class Fake(Sessao):
            def execute(self, statement, params):
                execucoes.append(params)
                return Resultado()

        r = acesso.observar_acesso(cfg(), tenant(), 5, sessao_factory=Fake, relogio=relogio)
        self.assertEqual(execucoes, [{"empresa_id": 1}])
        self.assertIn("EMPRESA_INDISPONIVEL", r.limitacoes)
        self.assertFalse(r.decisao.permitido)


class LogsTest(unittest.TestCase):
    def test_log_sem_dados_sensiveis(self):
        config = acesso.carregar_configuracao("observe", (123456,), convencao=CONV, segredo_identificador=SEGREDO)
        leitor = Leitor(erro=RuntimeError("cpf=123.456.789-00 senha=abc host=db.interno"))
        with self.assertLogs("smarttec.commercial_access", "DEBUG") as capturado:
            observar(config, ctx=tenant(123456, 987654), modulo=42, leitor=leitor)
            observar(config, ctx=tenant(123456, 987654), modulo=42, leitor=Leitor())
        texto = "\n".join(capturado.output)
        for proibido in ("123456", "987654", "cpf", "senha", "db.interno", "segredo-de-teste", "123.456"):
            self.assertNotIn(proibido, texto)
        self.assertIn("modulo=42", texto)

    def test_identificador_e_hmac_estavel_e_nao_reversivel(self):
        c1 = acesso.carregar_configuracao("observe", (1,), convencao=CONV, segredo_identificador=SEGREDO)
        c2 = acesso.carregar_configuracao("observe", (1,), convencao=CONV, segredo_identificador=SEGREDO + b"x")
        a, b = acesso._identificador(c1, 1), acesso._identificador(c2, 1)
        self.assertEqual(a, acesso._identificador(c1, 1))
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 16)
        self.assertEqual(acesso._identificador(cfg(), 1), "-")

    def test_log_nao_inclui_excecao_nem_sql(self):
        leitura = ev.ResultadoLeitura(pol.EvidenciasComerciais(), (ev.MotivoLeitura.FALHA_CONSULTA,))
        with self.assertLogs("smarttec.commercial_access", "DEBUG") as capturado:
            observar(cfg(), leitor=Leitor(resultado=leitura))
        texto = "\n".join(capturado.output)
        self.assertNotIn("SELECT", texto)
        self.assertNotIn("Traceback", texto)
        self.assertIn("FALHA_CONSULTA", texto)

    def test_falha_do_logger_nao_derruba(self):
        class Quebrado(Exception):
            pass

        original = acesso.logger.info
        acesso.logger.info = lambda *a, **k: (_ for _ in ()).throw(Quebrado())
        try:
            r, _ = observar(cfg(), leitor=Leitor())
        finally:
            acesso.logger.info = original
        self.assertFalse(r.bloqueia)
        self.assertTrue(r.observado)


class EscopoDoModuloTest(unittest.TestCase):
    def test_modulo_nao_importa_framework_nem_ambiente(self):
        from pathlib import Path

        fonte = (Path(__file__).resolve().parents[1] / "app" / "tenant" / "commercial_access.py").read_text(encoding="utf-8")
        for proibido in ("os.environ", "getenv", "settings", "fastapi", "HTTPException", "create_engine",
                         "psycopg", "INSERT", "UPDATE ", "DELETE ", "commit("):
            self.assertNotIn(proibido, fonte, proibido)


if __name__ == "__main__":
    unittest.main()
