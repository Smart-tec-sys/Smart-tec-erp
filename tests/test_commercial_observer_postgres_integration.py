"""Homologacao integrada do observador comercial (4C.13) em PostgreSQL real.

Pool dedicado + adaptador + observacao, somente no cluster temporario
descartavel 127.0.0.1:55433, banco smarttec_4c3d_homolog, com credencial
ficticia. Nao usa a configuracao de conexao do ERP nem .env. Os dados ficticios
sao gravados (commit) apenas para que a sessao independente do observador os
enxergue; ao final todas as tabelas do banco descartavel sao esvaziadas e a
ausencia de residuos e verificada. A convencao America/Sao_Paulo e FICTICIA.
O modo observe e instanciado apenas aqui, em memoria; nada e ativado no ERP.
"""
import json
import logging
import re
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.tenant import commercial_access as acesso
from app.tenant import commercial_observer_adapter as adaptador
from app.tenant.commercial_evidence import ConvencaoTemporal, ler_evidencias_comerciais
from app.tenant.commercial_observer_adapter import criar_fabrica_sessao, criar_observador
from app.tenant.commercial_observer_pool import ConfiguracaoPool, criar_pool_observacao
from app.tenant.commercial_policy import ConsultaAcesso, MotivoAcesso, avaliar_acesso_comercial
from app.tenant.context import TenantContext

HOST = "127.0.0.1"
PORTA = 55433
BANCO = "smarttec_4c3d_homolog"
RAIZ = Path(r"C:\Users\valmi\AppData\Local\Temp\smarttec-4c3a-pg18-31fb28b7101d49f19d7ec8df1319d5c3")
DATA_DIR = (RAIZ / "data").as_posix().lower()
TABELAS = {
    "assinaturas_saas", "auditoria_plataforma", "contas_financeiras", "empresa_modulos_saas",
    "empresas", "formas_pagamento", "modulos_saas", "pagamentos_saas", "pedidos_modulos_saas",
    "plano_modulos_saas", "planos_saas", "plataforma_equipe", "plataforma_funcoes", "usuarios",
}
SP = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc
CONV = ConvencaoTemporal(fuso_comercial=SP, fuso_timestamps_sem_fuso=SP)
SEGREDO_ID = b"segredo-ficticio-4c13"
TIMEOUT_LEITURA_S = 2.0
FOLGA_S = 0.75
EMAIL = "observador-4c13@example.invalid"
NOME_EMPRESA = "Empresa Ficticia Observada"


def _credencial():
    partes = (RAIZ / "test-only.pgpass").read_text().splitlines()[0].split(":")
    if partes[0] != HOST or partes[1] != str(PORTA):
        raise RuntimeError("credencial ficticia nao corresponde ao cluster temporario")
    return partes[3], ":".join(partes[4:])


def _url(banco=BANCO):
    usuario, senha = _credencial()
    return URL.create("postgresql+psycopg2", username=usuario, password=senha,
                      host=HOST, port=PORTA, database=banco)


def _guarda(conn):
    usuario, porta, banco, datadir, versao = conn.execute(text(
        "SELECT current_user, inet_server_port(), current_database(),"
        " current_setting('data_directory'), current_setting('server_version')"
    )).one()
    if (porta != PORTA or banco != BANCO or not usuario.startswith("test4c3a_")
            or datadir.replace("\\", "/").lower() != DATA_DIR or not versao.startswith("18.")):
        raise RuntimeError("DESTINO INVALIDO: execucao interrompida")
    tabelas = {r[0] for r in conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
    if tabelas != TABELAS:
        raise RuntimeError("ESQUEMA INESPERADO: execucao interrompida")


def _contagem(conn):
    return {t: conn.execute(text(f"SELECT count(*) FROM public.{t}")).scalar_one() for t in sorted(TABELAS)}


def _ins(conn, tabela, **cols):
    valores = ", ".join(f"CAST(:{k} AS jsonb)" if k == "detalhes" else f":{k}" for k in cols)
    return conn.execute(text(f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({valores}) RETURNING id"),
                        cols).scalar_one()


def _semear(conn):
    hoje = datetime.now(SP).date()
    inicio, fim = hoje - timedelta(days=5), hoje + timedelta(days=25)
    pago_em = datetime.now(SP).replace(tzinfo=None) - timedelta(days=10)
    usuario = _ins(conn, "usuarios", nome="Usuario Ficticio", email=EMAIL)
    funcao = _ins(conn, "plataforma_funcoes", codigo="F", nome="F")
    equipe = _ins(conn, "plataforma_equipe", usuario_id=usuario, funcao_id=funcao)
    plano = _ins(conn, "planos_saas", codigo="P", nome="P", produto="X", periodicidade="MENSAL")
    mod = {k: _ins(conn, "modulos_saas", codigo=k, nome=k, produto="X") for k in ("M", "N")}
    _ins(conn, "plano_modulos_saas", plano_id=plano, modulo_id=mod["M"], incluido=True)
    _ins(conn, "plano_modulos_saas", plano_id=plano, modulo_id=mod["N"], incluido=False)
    ids = {}
    for chave in ("A", "B", "C"):
        ids[chave] = _ins(conn, "empresas", nome=NOME_EMPRESA, slug=f"observada-4c13-{chave.lower()}", status="ATIVA")
    for chave in ("A", "B"):
        e = ids[chave]
        a = _ins(conn, "assinaturas_saas", empresa_id=e, plano_id=plano, status="ATIVA", periodicidade="MENSAL",
                 data_inicio_assinatura=inicio, data_vencimento=fim)
        p = _ins(conn, "pagamentos_saas", empresa_id=e, assinatura_id=a, tipo="ASSINATURA", status="PAGO",
                 valor=10, ciclo_inicio=inicio, ciclo_fim=fim, pago_em=pago_em)
        _ins(conn, "auditoria_plataforma", empresa_afetada_id=e, equipe_id=equipe, usuario_id=usuario,
             acao="ASSINATURA_PAGAMENTO_CONFIRMADO", recurso="pagamentos_saas", recurso_id=str(p),
             detalhes=json.dumps({"assinatura_id": a, "ciclo_inicio": inicio.isoformat(),
                                  "ciclo_fim": fim.isoformat()}),
             criado_em=pago_em + timedelta(hours=1))
        _ins(conn, "empresa_modulos_saas", empresa_id=e, modulo_id=mod["M"], assinatura_id=a, origem="PLANO",
             status="ATIVO", data_inicio=inicio, data_fim=fim, periodicidade="MENSAL")
    return ids, mod


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(_url(), poolclass=NullPool, connect_args={"connect_timeout": 5})
        cls.addClassCleanup(cls.engine.dispose)
        with cls.engine.connect() as conn:
            _guarda(conn)
            if any(_contagem(conn).values()):
                raise RuntimeError("banco de homologacao ja possui registros: interrompido")
        cls.addClassCleanup(cls._limpar)
        with cls.engine.begin() as conn:
            _guarda(conn)
            cls.ids, cls.mod = _semear(conn)
        with cls.engine.connect() as conn:
            cls.semeado = _contagem(conn)

    @classmethod
    def _limpar(cls):
        with cls.engine.begin() as conn:
            _guarda(conn)
            atual = _contagem(conn)
            conn.execute(text("TRUNCATE " + ", ".join(f"public.{t}" for t in sorted(TABELAS))
                              + " RESTART IDENTITY CASCADE"))
        with cls.engine.connect() as conn:
            residual = {t: n for t, n in _contagem(conn).items() if n}
        assert not residual, f"dados residuais: {residual}"
        assert atual == cls.semeado, f"os testes alteraram o banco: {atual} != {cls.semeado}"

    def setUp(self):
        self.conn = self.engine.connect()
        self.tx = self.conn.begin()
        _guarda(self.conn)

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    def pool(self, cfg=None, banco=BANCO):
        p = criar_pool_observacao(_url(banco), cfg or ConfiguracaoPool(
            tamanho=2, excesso_maximo=0, espera_conexao_s=0.5, timeout_conexao_s=1))
        self.addCleanup(p.fechar)
        return p

    def observador(self, pool, piloto=None, **kw):
        piloto = (self.ids["A"], self.ids["C"]) if piloto is None else piloto
        return criar_observador("observe", piloto, session_factory=pool.session_factory, convencao=CONV,
                                timeout_leitura_s=kw.pop("timeout", TIMEOUT_LEITURA_S),
                                segredo_identificador=SEGREDO_ID, **kw)

    def tenant(self, chave="A"):
        return TenantContext(empresa_id=self.ids[chave], user_id=1)

    def conexoes_externas(self):
        return self.conn.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname=:b AND pid<>pg_backend_pid()"),
            {"b": BANCO}).scalar_one()

    def direta(self, chave, modulo):
        agora = datetime.now(UTC)
        leitura = ler_evidencias_comerciais(self.conn, self.tenant(chave), agora=agora, convencao=CONV)
        return avaliar_acesso_comercial(ConsultaAcesso(self.ids[chave], self.mod[modulo], agora), leitura.evidencias)


class ObservacaoTest(Base):
    def test_01_off_nao_consulta_nem_inicia_pool(self):
        p = self.pool()
        chamadas = []
        for modo in (None, "off", "enforce", "valor-invalido"):
            obs = criar_observador(modo, (self.ids["A"],), session_factory=lambda: chamadas.append(1),
                                   convencao=CONV)
            r = obs.observar(self.tenant("A"), self.mod["M"])
            self.assertFalse(r.observado)
            self.assertFalse(r.bloqueia)
            self.assertEqual(r.situacao, acesso.SituacaoObservacao.NAO_OBSERVADO_MODO)
        self.assertEqual(chamadas, [])
        self.assertFalse(p.iniciado)

    def test_02_piloto_observado_com_dados_ficticios_e_resposta_inalterada(self):
        p = self.pool()
        obs = self.observador(p)
        for modulo in ("M", "N"):
            esperado = self.direta("A", modulo)
            r = obs.observar(self.tenant("A"), self.mod[modulo])
            self.assertTrue(r.observado)
            self.assertEqual(r.situacao, acesso.SituacaoObservacao.AVALIADO)
            self.assertEqual((r.decisao.permitido, r.decisao.motivo), (esperado.permitido, esperado.motivo))
            self.assertFalse(r.bloqueia)
        self.assertEqual(obs.observar(self.tenant("A"), self.mod["M"]).decisao.motivo, MotivoAcesso.PAGO_PERMITIDO)
        self.assertFalse(obs.observar(self.tenant("A"), self.mod["N"]).decisao.permitido)
        self.assertEqual(p._engine.pool.checkedout(), 0)

    def test_03_fora_do_piloto_sem_consulta(self):
        p = self.pool()
        obs = self.observador(p)
        r = obs.observar(self.tenant("B"), self.mod["M"])
        self.assertFalse(r.observado)
        self.assertEqual(r.situacao, acesso.SituacaoObservacao.NAO_OBSERVADO_NAO_PILOTO)
        self.assertFalse(p.iniciado)

    def test_03b_piloto_sem_dados_e_isolado_da_empresa_com_dados(self):
        obs = self.observador(self.pool())
        r = obs.observar(self.tenant("C"), self.mod["M"])
        self.assertTrue(r.observado)
        self.assertFalse(r.decisao.permitido)

    def test_04_transacao_somente_leitura_e_timeouts_aplicados(self):
        p = self.pool()
        sessao = criar_fabrica_sessao(p.session_factory, 0.5)()
        try:
            linha = sessao.execute(text(
                "SELECT current_setting('transaction_read_only'), current_setting('statement_timeout'),"
                " current_setting('lock_timeout'), current_setting('idle_in_transaction_session_timeout')"), {}).one()
            self.assertEqual(tuple(linha), ("on", "400ms", "400ms", "400ms"))
            with self.assertRaises(DBAPIError) as ctx:
                sessao.execute(text("INSERT INTO usuarios (nome, email) VALUES ('x', 'x@example.invalid')"), {})
            self.assertEqual(ctx.exception.orig.pgcode, "25006")
        finally:
            sessao.rollback()
            sessao.close()
        comum = p.session_factory()
        try:
            linha = comum.execute(text(
                "SELECT current_setting('transaction_read_only'), current_setting('statement_timeout'),"
                " current_setting('lock_timeout')")).one()
            self.assertEqual(tuple(linha), ("off", "0", "0"))
        finally:
            comum.rollback()
            comum.close()

    def test_05_statement_timeout_efetivo(self):
        sessao = criar_fabrica_sessao(self.pool().session_factory, 0.5)()
        inicio = time.monotonic()
        try:
            with self.assertRaises(DBAPIError) as ctx:
                sessao.execute(text("SELECT pg_sleep(5)"), {})
        finally:
            sessao.rollback()
            sessao.close()
        decorrido = time.monotonic() - inicio
        self.assertEqual(ctx.exception.orig.pgcode, "57014")
        self.assertLess(decorrido, 1.5)
        print(f"\n[4C.13] statement_timeout=400ms: cancelado em {decorrido:.3f}s")

    def test_06_lock_timeout_efetivo(self):
        self.conn.execute(text("LOCK TABLE public.usuarios IN ACCESS EXCLUSIVE MODE"))
        sessao = criar_fabrica_sessao(self.pool().session_factory, 0.5)()
        inicio = time.monotonic()
        try:
            with self.assertRaises(DBAPIError) as ctx:
                sessao.execute(text("SELECT count(*) FROM public.usuarios"), {})
        finally:
            sessao.rollback()
            sessao.close()
        decorrido = time.monotonic() - inicio
        # lock_timeout e statement_timeout coincidem (400ms): qualquer um dos dois encerra a espera.
        self.assertIn(ctx.exception.orig.pgcode, ("55P03", "57014"))
        self.assertLess(decorrido, 1.5)
        print(f"\n[4C.13] espera por lock encerrada em {decorrido:.3f}s (sqlstate {ctx.exception.orig.pgcode})")

    def test_07_idle_in_transaction_timeout_efetivo(self):
        p = self.pool()
        sessao = criar_fabrica_sessao(p.session_factory, 0.5)()
        try:
            sessao.execute(text("SELECT 1"), {})
            time.sleep(0.9)
            with self.assertRaises(DBAPIError):
                sessao.execute(text("SELECT 1"), {})
        finally:
            for op in (sessao.rollback, sessao.close):
                try:
                    op()
                except Exception:
                    pass
        self.assertEqual(p._engine.pool.checkedout(), 0)

    def test_08_pool_esgotado_nao_trava_a_requisicao(self):
        p = self.pool(ConfiguracaoPool(tamanho=1, excesso_maximo=0, espera_conexao_s=0.3, timeout_conexao_s=1))
        obs = self.observador(p)
        ocupada = p.session_factory()
        ocupada.execute(text("SELECT 1"))
        try:
            inicio = time.monotonic()
            r = obs.observar(self.tenant("A"), self.mod["M"])
            decorrido = time.monotonic() - inicio
        finally:
            ocupada.rollback()
            ocupada.close()
        self.assertLess(decorrido, TIMEOUT_LEITURA_S + FOLGA_S)
        self.assertTrue(r.observado)
        self.assertFalse(r.bloqueia)
        self.assertFalse(r.decisao is not None and r.decisao.permitido)
        print(f"\n[4C.13] pool esgotado: observar retornou em {decorrido:.3f}s ({r.situacao.value}, {r.limitacoes})")
        apos = obs.observar(self.tenant("A"), self.mod["M"])
        self.assertTrue(apos.decisao.permitido)

    def test_09_falha_de_conexao_nao_propaga(self):
        p = self.pool(banco="banco_inexistente_4c13")
        obs = self.observador(p)
        inicio = time.monotonic()
        r = obs.observar(self.tenant("A"), self.mod["M"])
        decorrido = time.monotonic() - inicio
        self.assertTrue(r.observado)
        self.assertFalse(r.bloqueia)
        self.assertFalse(r.decisao is not None and r.decisao.permitido)
        self.assertLess(decorrido, TIMEOUT_LEITURA_S + FOLGA_S)
        print(f"\n[4C.13] falha de conexao: observar retornou em {decorrido:.3f}s ({r.situacao.value})")

    def test_10_orcamento_de_espera_com_leitura_bloqueada(self):
        self.conn.execute(text("LOCK TABLE public.empresas, public.assinaturas_saas, public.pagamentos_saas,"
                               " public.empresa_modulos_saas, public.auditoria_plataforma"
                               " IN ACCESS EXCLUSIVE MODE"))
        obs = self.observador(self.pool())
        inicio = time.monotonic()
        r = obs.observar(self.tenant("A"), self.mod["M"])
        decorrido = time.monotonic() - inicio
        self.assertFalse(r.bloqueia)
        self.assertFalse(r.decisao is not None and r.decisao.permitido)
        self.assertLess(decorrido, TIMEOUT_LEITURA_S + FOLGA_S)
        print(f"\n[4C.13] leitura bloqueada: observar retornou em {decorrido:.3f}s ({r.situacao.value}, {r.limitacoes})")

    def test_11_sessoes_e_conexoes_encerradas(self):
        base = self.conexoes_externas()
        p = self.pool()
        obs = self.observador(p)
        for _ in range(3):
            obs.observar(self.tenant("A"), self.mod["M"])
        self.assertEqual(p._engine.pool.checkedout(), 0)
        self.assertEqual(self.conn.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname=:b AND pid<>pg_backend_pid()"
            " AND state LIKE 'idle in transaction%'"), {"b": BANCO}).scalar_one(), 0)
        p.fechar()
        for _ in range(20):
            if self.conexoes_externas() == base:
                break
            time.sleep(0.1)
        self.assertEqual(self.conexoes_externas(), base)
        self.assertTrue(p.fechado)

    def test_12_logs_e_representacoes_sem_dados_sensiveis(self):
        usuario, senha = _credencial()
        p = self.pool()
        pf = self.pool(banco="banco_inexistente_4c13")
        resultados = []
        with self.assertLogs("smarttec.commercial_access", level="INFO") as capturado:
            resultados.append(self.observador(p).observar(self.tenant("A"), self.mod["M"]))
            resultados.append(self.observador(pf).observar(self.tenant("A"), self.mod["M"]))
        texto = "\n".join(capturado.output + [repr(r) for r in resultados] + [repr(p), repr(pf), repr(p.configuracao)]
                          + [repr(self.observador(p).config)])
        for proibido in (senha, usuario, HOST, str(PORTA), BANCO, EMAIL, NOME_EMPRESA, "observada-4c13",
                         "banco_inexistente", SEGREDO_ID.decode(), "postgresql"):
            self.assertNotIn(proibido, texto)
        self.assertTrue(all(re.search(r"empresa=[0-9a-f]{16}\b", linha) for linha in capturado.output))

    def test_13_nenhum_bloqueio_e_banco_inalterado(self):
        obs = self.observador(self.pool())
        antes = _contagem(self.conn)
        for chave in ("A", "B", "C"):
            for modulo in ("M", "N"):
                self.assertFalse(obs.observar(self.tenant(chave), self.mod[modulo]).bloqueia)
        self.assertEqual(antes, _contagem(self.conn))
        enforce = criar_observador("enforce", (self.ids["A"],), session_factory=lambda: None, convencao=CONV)
        self.assertIs(enforce.config.modo, acesso.ModoComercial.OFF)
        self.assertTrue(enforce.config.enforce_solicitado)
        self.assertFalse(enforce.observar(self.tenant("A"), self.mod["M"]).bloqueia)

    def test_14_orcamento_coerente_com_a_configuracao(self):
        cfg = ConfiguracaoPool(tamanho=2, excesso_maximo=0, espera_conexao_s=0.5, timeout_conexao_s=1)
        banco_ms = adaptador.timeout_banco_ms(TIMEOUT_LEITURA_S)
        self.assertLess(cfg.espera_conexao_s, TIMEOUT_LEITURA_S)
        self.assertLess(cfg.timeout_conexao_s, TIMEOUT_LEITURA_S)
        self.assertLess(banco_ms / 1000, TIMEOUT_LEITURA_S)
        # A soma dos limites individuais pode ultrapassar o orcamento; quem o garante e a espera da thread.
        self.assertGreater(max(cfg.espera_conexao_s, cfg.timeout_conexao_s) + banco_ms / 1000, TIMEOUT_LEITURA_S)


class IsolamentoDoAmbienteTest(unittest.TestCase):
    def test_fonte_sem_url_de_aplicacao_ou_outros_destinos(self):
        fonte = Path(__file__).read_text(encoding="utf-8")
        for proibido in ("DATABASE" + "_URL", "os." + "environ", "from app." + "database", "get" + "env"):
            self.assertNotIn(proibido, fonte)
        self.assertEqual(re.findall(r"\b54\d\d\b", fonte), [])


if __name__ == "__main__":
    unittest.main()
