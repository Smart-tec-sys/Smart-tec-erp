"""Homologacao do leitor comercial (4C.2) + politica (4C.1) em PostgreSQL real.

Somente o cluster temporario descartavel 127.0.0.1:55433, banco
smarttec_4c3d_homolog, com credencial ficticia. Nao usa DATABASE_URL, .env nem
configuracao do ERP. Cada cenario roda em uma transacao que sofre ROLLBACK.
A convencao America/Sao_Paulo abaixo e FICTICIA, apenas de teste.
"""
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from app.tenant.commercial_evidence import (
    ConvencaoTemporal, MotivoLeitura, ler_evidencias_comerciais,
)
from app.tenant.commercial_policy import (
    ConsultaAcesso, EstadoPagamento, MotivoAcesso, avaliar_acesso_comercial,
)
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
AGORA = datetime(2026, 10, 17, 12, 0, tzinfo=SP)
M, N = "M", "N"  # chaves dos modulos do cenario base


def _credencial():
    partes = (RAIZ / "test-only.pgpass").read_text().splitlines()[0].split(":")
    if partes[0] != HOST or partes[1] != str(PORTA):
        raise RuntimeError("credencial ficticia nao corresponde ao cluster temporario")
    return partes[3], ":".join(partes[4:])


def _guarda(conn):
    """Interrompe se a conexao nao for exatamente o banco descartavel."""
    usuario, porta, banco, datadir, versao = conn.execute(text(
        "SELECT current_user, inet_server_port(), current_database(),"
        " current_setting('data_directory'), current_setting('server_version')"
    )).one()
    if (porta != PORTA or banco != BANCO or not usuario.startswith("test4c3a_")
            or datadir.replace("\\", "/").lower() != DATA_DIR or not versao.startswith("18.")):
        raise RuntimeError("DESTINO INVALIDO: execucao interrompida")
    tabelas = {r[0] for r in conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
    if tabelas != TABELAS:
        raise RuntimeError("ESQUEMA INESPERADO: execucao interrompida")


def _contagem(conn):
    return {t: conn.execute(text(f"SELECT count(*) FROM public.{t}")).scalar_one() for t in sorted(TABELAS)}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        usuario, senha = _credencial()
        url = URL.create("postgresql+psycopg2", username=usuario, password=senha,
                         host=HOST, port=PORTA, database=BANCO)
        cls.engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=False)
        with cls.engine.connect() as conn:
            _guarda(conn)
            antes = _contagem(conn)
        if any(antes.values()):
            raise RuntimeError("banco de homologacao ja possui registros: interrompido")

    @classmethod
    def tearDownClass(cls):
        try:
            with cls.engine.connect() as conn:
                _guarda(conn)
                residual = {t: n for t, n in _contagem(conn).items() if n}
        finally:
            cls.engine.dispose()
        assert not residual, f"dados residuais: {residual}"

    def setUp(self):
        self.conn = self.engine.connect()
        self.tx = self.conn.begin()
        _guarda(self.conn)
        self.c = 0
        self.empresa = self.nova_empresa()
        self.usuario = self.ins("usuarios", nome="Teste", email=f"t{self.seq()}@example.invalid")
        funcao = self.ins("plataforma_funcoes", codigo="F", nome="F")
        self.equipe = self.ins("plataforma_equipe", usuario_id=self.usuario, funcao_id=funcao)
        self.plano = self.ins("planos_saas", codigo="P", nome="P", produto="X", periodicidade="MENSAL")
        self.mod = {
            M: self.ins("modulos_saas", codigo="M", nome="M", produto="X"),
            N: self.ins("modulos_saas", codigo="N", nome="N", produto="X"),
        }
        self.ins("plano_modulos_saas", plano_id=self.plano, modulo_id=self.mod[M], incluido=True)
        self.ins("plano_modulos_saas", plano_id=self.plano, modulo_id=self.mod[N], incluido=False)

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    # ---- fabrica de dados ficticios ----
    def seq(self):
        self.c += 1
        return self.c

    def ins(self, tabela, **cols):
        valores = ", ".join(f"CAST(:{k} AS jsonb)" if k == "detalhes" else f":{k}" for k in cols)
        sql = f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({valores}) RETURNING id"
        return self.conn.execute(text(sql), cols).scalar_one()

    def nova_empresa(self, status="ATIVA"):
        n = self.seq() if hasattr(self, "c") else 0
        return self.ins("empresas", nome=f"Empresa ficticia {n}", slug=f"ficticia-{n}-{id(self)}", status=status)

    def auditar(self, empresa, acao, recurso, recurso_id, detalhes, criado_em):
        return self.ins(
            "auditoria_plataforma", empresa_afetada_id=empresa, equipe_id=self.equipe,
            usuario_id=self.usuario, acao=acao, recurso=recurso, recurso_id=str(recurso_id),
            detalhes=json.dumps(detalhes), criado_em=criado_em)

    def assinatura(self, empresa=None, status="ATIVA", inicio=date(2026, 10, 1), fim=date(2026, 11, 1), **extra):
        return self.ins(
            "assinaturas_saas", empresa_id=empresa or self.empresa, plano_id=self.plano, status=status,
            periodicidade="MENSAL", data_inicio_assinatura=inicio, data_vencimento=fim, **extra)

    def ciclo(self, assinatura, inicio, fim, status="PAGO", pago_em=None, confirmar=True, empresa=None):
        empresa = empresa or self.empresa
        pago = pago_em if status == "PAGO" else None
        pid = self.ins(
            "pagamentos_saas", empresa_id=empresa, assinatura_id=assinatura, tipo="ASSINATURA",
            status=status, valor=10, ciclo_inicio=inicio, ciclo_fim=fim, pago_em=pago)
        if status == "PAGO" and confirmar:
            self.auditar(empresa, "ASSINATURA_PAGAMENTO_CONFIRMADO", "pagamentos_saas", pid,
                         {"assinatura_id": assinatura, "ciclo_inicio": inicio.isoformat(),
                          "ciclo_fim": fim.isoformat()}, pago + timedelta(hours=1))
        return pid

    def paga(self, inicio=date(2026, 10, 1), fim=date(2026, 11, 1), pago_em=datetime(2026, 9, 20, 9, 0),
             confirmar=True, status="ATIVA"):
        a = self.assinatura(status=status, inicio=inicio, fim=fim)
        self.ciclo(a, inicio, fim, pago_em=pago_em, confirmar=confirmar)
        return a

    def concessao_plano(self, assinatura, modulo=M, inicio=date(2026, 10, 1), fim=date(2026, 11, 1),
                        origem="PLANO", status="ATIVO"):
        return self.ins(
            "empresa_modulos_saas", empresa_id=self.empresa, modulo_id=self.mod[modulo],
            assinatura_id=assinatura, origem=origem, status=status, data_inicio=inicio,
            data_fim=fim, periodicidade="MENSAL")

    def avaliar(self, modulo=M, agora=AGORA, conv=CONV, empresa=None, sessao=None):
        empresa = empresa or self.empresa
        leitura = ler_evidencias_comerciais(
            sessao or self.conn, TenantContext(empresa_id=empresa, user_id=1), agora=agora, convencao=conv)
        decisao = avaliar_acesso_comercial(
            ConsultaAcesso(empresa, self.mod[modulo], agora.astimezone(UTC)), leitura.evidencias)
        return leitura, decisao

    def assertDecisao(self, decisao, permitido, motivo):
        self.assertEqual((decisao.permitido, decisao.motivo), (permitido, motivo))


class CenariosDeAssinatura(Base):
    def test_01_assinatura_paga_com_evidencias_completas(self):
        a = self.paga()
        self.concessao_plano(a)
        leitura, decisao = self.avaliar()
        self.assertEqual(leitura.limitacoes, ())
        self.assertTrue(leitura.evidencias.completas)
        self.assertDecisao(decisao, True, MotivoAcesso.PAGO_PERMITIDO)
        ciclo, = leitura.evidencias.ciclos
        self.assertIsNotNone(ciclo.confirmacao)
        self.assertEqual(ciclo.pago_em, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    def test_02_assinatura_sem_pagamento(self):
        a = self.assinatura()
        self.concessao_plano(a)
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_03_pagamento_sem_confirmacao_administrativa(self):
        a = self.paga(confirmar=False)
        self.concessao_plano(a)
        leitura, decisao = self.avaliar()
        self.assertIn(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE, leitura.limitacoes)
        self.assertDecisao(decisao, False, MotivoAcesso.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)

    def test_04_assinatura_e_pagamento_de_empresas_diferentes(self):
        outra = self.nova_empresa()
        a = self.assinatura()
        self.concessao_plano(a)
        # cobranca da empresa B apontando para a assinatura da empresa A
        self.ciclo(a, date(2026, 10, 1), date(2026, 11, 1), pago_em=datetime(2026, 9, 20, 9), empresa=outra)
        leitura_b, decisao_b = self.avaliar(empresa=outra)
        self.assertEqual(leitura_b.limitacoes, (MotivoLeitura.VINCULO_DIVERGENTE,))
        self.assertDecisao(decisao_b, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
        # a empresa A nao enxerga a cobranca da B e nao ganha acesso por ela
        leitura_a, decisao_a = self.avaliar()
        self.assertEqual(leitura_a.evidencias.ciclos, ())
        self.assertDecisao(decisao_a, False, MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_isolamento_entre_empresas_com_dados_completos(self):
        outra = self.nova_empresa()
        a = self.paga()
        self.concessao_plano(a)
        leitura, decisao = self.avaliar(empresa=outra)
        self.assertDecisao(decisao, False, MotivoAcesso.ASSINATURA_AUSENTE)
        self.assertEqual(leitura.evidencias.ciclos, ())
        self.assertEqual(leitura.evidencias.concessoes, ())

    def test_06_inicio_futuro(self):
        a = self.paga(inicio=date(2026, 11, 1), fim=date(2026, 12, 1), pago_em=datetime(2026, 10, 10, 9))
        self.concessao_plano(a, inicio=date(2026, 11, 1), fim=date(2026, 12, 1))
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.COBERTURA_FUTURA)

    def test_07_periodo_encerrado(self):
        a = self.paga(inicio=date(2026, 9, 1), fim=date(2026, 10, 1), pago_em=datetime(2026, 8, 20, 9))
        self.concessao_plano(a, inicio=date(2026, 9, 1), fim=date(2026, 10, 1))
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.COBERTURA_ENCERRADA)

    def test_08_renovacao_pendente_preserva_cobertura_anterior(self):
        a = self.paga()
        self.concessao_plano(a)
        self.ciclo(a, date(2026, 11, 1), date(2026, 12, 1), status="PENDENTE")
        leitura, decisao = self.avaliar()
        self.assertEqual(len(leitura.evidencias.ciclos), 2)
        self.assertDecisao(decisao, True, MotivoAcesso.PAGO_PERMITIDO)

    def test_09_suspensao(self):
        a = self.paga(status="SUSPENSA")
        self.concessao_plano(a)
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.ASSINATURA_SUSPENSA)

    def test_09b_modulo_suspenso_bloqueia(self):
        a = self.paga()
        self.concessao_plano(a, status="SUSPENSO")
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.MODULO_BLOQUEADO)

    def test_09c_modulo_inativo_no_catalogo_bloqueia(self):
        a = self.paga()
        self.concessao_plano(a)
        self.conn.execute(text("UPDATE modulos_saas SET ativo=false WHERE id=:i"), {"i": self.mod[M]})
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.MODULO_BLOQUEADO)

    def test_10_trial_valido(self):
        a = self.assinatura(status="TRIAL", inicio=None, fim=None,
                            data_inicio_trial=date(2026, 10, 10), data_fim_trial=date(2026, 10, 24))
        self.concessao_plano(a, inicio=date(2026, 10, 10), fim=date(2026, 10, 24), origem="TRIAL")
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, True, MotivoAcesso.TRIAL_PERMITIDO)

    def test_10b_trial_vencido(self):
        a = self.assinatura(status="TRIAL", inicio=None, fim=None,
                            data_inicio_trial=date(2026, 9, 1), data_fim_trial=date(2026, 9, 8))
        self.concessao_plano(a, inicio=date(2026, 9, 1), fim=date(2026, 9, 8), origem="TRIAL")
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, False, MotivoAcesso.COBERTURA_ENCERRADA)

    def test_11_modulo_nao_contratado(self):
        a = self.paga()
        self.concessao_plano(a)
        _, decisao = self.avaliar(modulo=N)
        self.assertDecisao(decisao, False, MotivoAcesso.MODULO_NAO_CONTRATADO)

    def test_11b_modulo_do_plano_marcado_nao_incluido(self):
        a = self.paga()
        self.concessao_plano(a, modulo=N)
        _, decisao = self.avaliar(modulo=N)
        self.assertDecisao(decisao, False, MotivoAcesso.CONCESSAO_NAO_COMPROVADA)

    def _avulso(self, confirmar_pagamento=True):
        a = self.paga()
        pedido = self.ins("pedidos_modulos_saas", empresa_id=self.empresa, modulo_id=self.mod[N],
                          status="ATIVADO", periodicidade="MENSAL")
        pago = datetime(2026, 10, 10, 8, 0)
        pag = self.ins("pagamentos_saas", empresa_id=self.empresa, assinatura_id=None,
                       pedido_modulo_id=pedido, tipo="MODULO_AVULSO", status="PAGO", valor=5, pago_em=pago)
        if confirmar_pagamento:
            self.auditar(self.empresa, "PAGAMENTO_PEDIDO_CONFIRMADO", "pagamentos_saas", pag,
                         {"pedido_id": pedido, "modulo_id": self.mod[N]}, datetime(2026, 10, 10, 9, 0))
        g = self.concessao_plano(None, modulo=N, inicio=date(2026, 10, 10), fim=date(2026, 11, 10),
                                 origem="AVULSO")
        self.auditar(self.empresa, "MODULO_ATIVADO_POR_PEDIDO", "empresa_modulos_saas", g,
                     {"modulo_id": self.mod[N], "origem": "AVULSO", "periodicidade": "MENSAL",
                      "data_fim": "2026-11-10", "pedido_id": pedido}, datetime(2026, 10, 10, 10, 0))
        self.concessao_plano(a)
        return a

    def test_12_modulo_avulso_autorizado(self):
        self._avulso()
        leitura, decisao = self.avaliar(modulo=N)
        self.assertEqual(leitura.limitacoes, ())
        self.assertDecisao(decisao, True, MotivoAcesso.PAGO_PERMITIDO)

    def test_12b_avulso_sem_confirmacao_financeira_nao_concede(self):
        self._avulso(confirmar_pagamento=False)
        leitura, decisao = self.avaliar(modulo=N)
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE,))
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)

    def test_13_contratos_conflitantes(self):
        a = self.paga()
        self.concessao_plano(a)
        self.assinatura(inicio=date(2026, 10, 1), fim=date(2026, 11, 1))
        leitura, decisao = self.avaliar()
        self.assertIn(MotivoLeitura.CONTRATOS_CONFLITANTES, leitura.limitacoes)
        self.assertDecisao(decisao, False, MotivoAcesso.CONTRATOS_CONFLITANTES)

    def test_13b_ciclos_conflitantes(self):
        a = self.assinatura(inicio=date(2026, 10, 1), fim=date(2026, 12, 1))
        self.concessao_plano(a, fim=date(2026, 12, 1))
        pago = datetime(2026, 9, 20, 9)
        self.ciclo(a, date(2026, 10, 1), date(2026, 11, 1), pago_em=pago)
        self.ciclo(a, date(2026, 10, 15), date(2026, 11, 15), pago_em=pago)
        leitura, decisao = self.avaliar()
        self.assertIn(MotivoLeitura.CICLOS_CONFLITANTES, leitura.limitacoes)
        self.assertDecisao(decisao, False, MotivoAcesso.CICLOS_CONFLITANTES)

    def test_13c_cancelada_sem_cobertura_nao_compete_com_nova_assinatura(self):
        self.assinatura(status="CANCELADA", inicio=date(2026, 5, 1), fim=date(2026, 6, 1))
        a = self.paga()
        self.concessao_plano(a)
        leitura, decisao = self.avaliar()
        self.assertEqual(len(leitura.evidencias.assinaturas_candidatas), 1)
        self.assertDecisao(decisao, True, MotivoAcesso.PAGO_PERMITIDO)

    def test_14_ausencia_de_dados(self):
        leitura, decisao = self.avaliar()
        self.assertTrue(leitura.evidencias.completas)
        self.assertDecisao(decisao, False, MotivoAcesso.ASSINATURA_AUSENTE)

    def test_14b_empresa_inexistente_ou_inativa(self):
        leitura, decisao = self.avaliar(empresa=2_000_000_000)
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.EMPRESA_INDISPONIVEL,))
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
        inativa = self.nova_empresa(status="INATIVA")
        leitura, decisao = self.avaliar(empresa=inativa)
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.EMPRESA_INDISPONIVEL,))
        self.assertFalse(decisao.permitido)

    def test_auditoria_de_outra_empresa_nao_comprova_pagamento(self):
        outra = self.nova_empresa()
        a = self.paga(confirmar=False)
        self.concessao_plano(a)
        pid = self.conn.execute(text("SELECT id FROM pagamentos_saas WHERE assinatura_id=:a"), {"a": a}).scalar_one()
        self.auditar(outra, "ASSINATURA_PAGAMENTO_CONFIRMADO", "pagamentos_saas", pid,
                     {"assinatura_id": a, "ciclo_inicio": "2026-10-01", "ciclo_fim": "2026-11-01"},
                     datetime(2026, 9, 20, 10))
        leitura, decisao = self.avaliar()
        self.assertIn(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE, leitura.limitacoes)
        self.assertFalse(decisao.permitido)

    def test_auditoria_com_periodo_divergente_nao_concede(self):
        a = self.paga(confirmar=False)
        self.concessao_plano(a)
        pid = self.conn.execute(text("SELECT id FROM pagamentos_saas WHERE assinatura_id=:a"), {"a": a}).scalar_one()
        self.auditar(self.empresa, "ASSINATURA_PAGAMENTO_CONFIRMADO", "pagamentos_saas", pid,
                     {"assinatura_id": a, "ciclo_inicio": "2026-10-01", "ciclo_fim": "2026-12-01"},
                     datetime(2026, 9, 20, 10))
        leitura, decisao = self.avaliar()
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE,))
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)


class FalhasDeConsulta(Base):
    def test_15_falha_de_consulta_sql_real(self):
        class SessaoQuebrada:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, statement, params):
                return self.conn.execute(text("SELECT * FROM tabela_inexistente_4c3"))

        self.conn.begin_nested()  # protege a transacao do teste do erro de consulta
        leitura, decisao = self.avaliar(sessao=SessaoQuebrada(self.conn))
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.FALHA_CONSULTA,))
        self.assertFalse(leitura.evidencias.completas)
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)

    def test_15b_excecao_do_chamador(self):
        class SessaoQueFalha:
            def execute(self, statement, params):
                raise ConnectionError("segredo-nao-deve-vazar")

        leitura, _ = self.avaliar(sessao=SessaoQueFalha())
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.FALHA_CONSULTA,))
        self.assertNotIn("segredo", repr(leitura))

    def test_consulta_executa_em_transacao_somente_leitura(self):
        a = self.paga()
        self.concessao_plano(a)
        self.conn.execute(text("SET TRANSACTION READ ONLY"))
        _, decisao = self.avaliar()
        self.assertDecisao(decisao, True, MotivoAcesso.PAGO_PERMITIDO)

    def test_leitura_nao_altera_o_banco(self):
        a = self.paga()
        self.concessao_plano(a)
        antes = _contagem(self.conn)
        self.avaliar()
        self.avaliar(modulo=N)
        self.assertEqual(antes, _contagem(self.conn))


class LimitesETemporalidade(Base):
    def setUp(self):
        super().setUp()
        self.a = self.paga()
        self.concessao_plano(self.a)

    def test_16_limite_exato_de_inicio_e_fim(self):
        inicio = datetime(2026, 10, 1, 0, 0, tzinfo=SP)
        fim = datetime(2026, 11, 1, 0, 0, tzinfo=SP)
        um_s = timedelta(seconds=1)
        casos = [
            (inicio - um_s, False, MotivoAcesso.COBERTURA_FUTURA),
            (inicio, True, MotivoAcesso.PAGO_PERMITIDO),
            (fim - um_s, True, MotivoAcesso.PAGO_PERMITIDO),
            (fim, False, MotivoAcesso.COBERTURA_ENCERRADA),
        ]
        for agora, permitido, motivo in casos:
            with self.subTest(agora=agora.isoformat()):
                _, decisao = self.avaliar(agora=agora)
                self.assertDecisao(decisao, permitido, motivo)

    def test_fuso_do_cluster_nao_altera_o_resultado(self):
        agora = datetime(2026, 10, 1, 0, 0, tzinfo=SP)
        resultados = []
        for fuso in ("UTC", "Asia/Tokyo"):
            self.conn.execute(text("SELECT set_config('TimeZone', :z, true)"), {"z": fuso})
            resultados.append(self.avaliar(agora=agora)[1])
        self.assertEqual(resultados[0], resultados[1])
        self.assertTrue(resultados[0].permitido)

    def test_conversao_depende_da_convencao_explicita(self):
        # 02:59:59Z de 01/10: antes da meia-noite de Sao Paulo (03:00Z), depois da meia-noite UTC.
        agora = datetime(2026, 10, 1, 2, 59, 59, tzinfo=UTC)
        utc = ConvencaoTemporal(fuso_comercial=UTC, fuso_timestamps_sem_fuso=UTC)
        self.assertDecisao(self.avaliar(agora=agora, conv=CONV)[1], False, MotivoAcesso.COBERTURA_FUTURA)
        self.assertDecisao(self.avaliar(agora=agora, conv=utc)[1], True, MotivoAcesso.PAGO_PERMITIDO)

    def test_timestamp_sem_fuso_e_convertido_pela_convencao(self):
        sp = self.avaliar()[0].evidencias.ciclos[0].pago_em
        utc = self.avaliar(conv=ConvencaoTemporal(UTC, UTC))[0].evidencias.ciclos[0].pago_em
        self.assertEqual(sp, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))
        self.assertEqual(utc, datetime(2026, 9, 20, 9, 0, tzinfo=UTC))

    def test_sem_convencao_nega_prova(self):
        leitura, decisao = self.avaliar(conv=ConvencaoTemporal())
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE,))
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)

    def test_pagamento_futuro_em_relacao_a_agora_nao_concede(self):
        agora = datetime(2026, 9, 20, 8, 0, tzinfo=SP)  # antes de pago_em (09:00 local)
        leitura, decisao = self.avaliar(agora=agora)
        # a confirmacao administrativa (10:00 local) tambem e posterior a "agora"
        self.assertEqual(leitura.limitacoes, (MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE,))
        self.assertDecisao(decisao, False, MotivoAcesso.EVIDENCIAS_INCOMPLETAS)


if __name__ == "__main__":
    unittest.main()
