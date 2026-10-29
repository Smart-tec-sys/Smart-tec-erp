"""Homologacao de concorrencia dos limites de usuarios (4D.4A) em PostgreSQL real.

Somente o cluster temporario descartavel 127.0.0.1:55433, banco
smarttec_4c3d_homolog, credencial ficticia. Nao usa a configuracao de conexao do
ERP nem .env. A tabela public.empresa_usuarios nao existe nesse banco; ela e criada
aqui (DDL identico ao da migration 20260830 fase 6b) e REMOVIDA ao final, mesmo
quando um teste falha. Nenhuma migration e executada e nada e ativado no ERP.
Planos e limites sao FICTICIOS, injetados por resolvedor; nao ha mapeamento Wix.
"""
import threading
import time
import unittest
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import membership_service as ms
from app.auth.seat_limits import SituacaoVaga as S, contar_usuarios_ativos

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
TIMEOUT_S = 15.0
DDL = """
CREATE TABLE public.empresa_usuarios (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    papel VARCHAR(20) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_empresa_usuarios_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_empresa_usuarios_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT uq_empresa_usuarios_empresa_usuario UNIQUE (empresa_id, usuario_id),
    CONSTRAINT ck_empresa_usuarios_papel CHECK (papel IN ('OWNER','ADMIN','USUARIO'))
)
"""


def _url():
    partes = (RAIZ / "test-only.pgpass").read_text().splitlines()[0].split(":")
    if partes[0] != HOST or partes[1] != str(PORTA):
        raise RuntimeError("credencial ficticia nao corresponde ao cluster temporario")
    return URL.create("postgresql+psycopg2",     username=partes[3], password=":".join(partes[4:]),
                      host=HOST, port=PORTA, database=BANCO)


def _guarda(conn):
    usuario, porta, banco, datadir, versao = conn.execute(text(
        "SELECT current_user, inet_server_port(), current_database(),"
        " current_setting('data_directory'), current_setting('server_version')"
    )).one()
    if (porta != PORTA or banco != BANCO or not usuario.startswith("test4c3a_")
            or datadir.replace("\\", "/").lower() != DATA_DIR or not versao.startswith("18.")):
        raise RuntimeError("DESTINO INVALIDO: execucao interrompida")


def _tabelas(conn):
    return {r[0] for r in conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))}


def _contagem(conn, tabelas):
    return {t: conn.execute(text(f"SELECT count(*) FROM public.{t}")).scalar_one() for t in sorted(tabelas)}


def limite(valor):
    return lambda sessao, empresa_id: valor


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.criada = False
        cls.engine = create_engine(
            _url(), poolclass=NullPool,
            connect_args={"connect_timeout": 5, "options": "-c lock_timeout=10000 -c statement_timeout=15000"})
        cls.addClassCleanup(cls.engine.dispose)
        with cls.engine.connect() as conn:
            _guarda(conn)
            if _tabelas(conn) != TABELAS:
                raise RuntimeError("ESQUEMA INESPERADO (ou empresa_usuarios ja existe): interrompido")
            if any(_contagem(conn, TABELAS).values()):
                raise RuntimeError("banco de homologacao ja possui registros: interrompido")
        cls.addClassCleanup(cls._limpar)
        with cls.engine.begin() as conn:
            _guarda(conn)
            conn.execute(text(DDL))
        cls.criada = True

    @classmethod
    def _limpar(cls):
        if not cls.criada:
            return
        try:
            with cls.engine.begin() as conn:
                _guarda(conn)
                conn.execute(text("TRUNCATE public.empresa_usuarios, public.usuarios, public.empresas"
                                  " RESTART IDENTITY CASCADE"))
        finally:
            with cls.engine.begin() as conn:
                _guarda(conn)
                conn.execute(text("DROP TABLE IF EXISTS public.empresa_usuarios"))
        with cls.engine.connect() as conn:
            assert _tabelas(conn) == TABELAS, f"esquema nao voltou as 14 tabelas: {_tabelas(conn)}"
            residual = {t: n for t, n in _contagem(conn, TABELAS).items() if n}
            assert not residual, f"dados residuais: {residual}"
            presas = conn.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                " AND pid <> pg_backend_pid() AND state IN ('idle in transaction', 'active')"
            )).scalar_one()
            assert presas == 0, f"sessoes presas: {presas}"

    def setUp(self):
        self.sql = []
        event.listen(self.engine, "before_cursor_execute", self._registrar)
        self.addCleanup(event.remove, self.engine, "before_cursor_execute", self._registrar)
        self.addCleanup(self._truncar)
        self.prox = 0

    def _registrar(self, conn, cur, stmt, *a):
        self.sql.append(stmt)

    def _truncar(self):
        with self.engine.begin() as conn:
            _guarda(conn)
            conn.execute(text("TRUNCATE public.empresa_usuarios, public.usuarios, public.empresas"
                              " RESTART IDENTITY CASCADE"))

    def empresa(self, status="ATIVA"):
        self.prox += 1
        with self.engine.begin() as conn:
            return conn.execute(text("INSERT INTO empresas (nome, slug, status) VALUES (:n, :s, :st) RETURNING id"),
                                {"n": f"Empresa Ficticia {self.prox}", "s": f"ficticia-4d4a-{self.prox}",
                                 "st": status}).scalar_one()

    def usuario(self):
        self.prox += 1
        with self.engine.begin() as conn:
            return conn.execute(text("INSERT INTO usuarios (nome, email, status) VALUES (:n, :e, 'ATIVO')"
                                     " RETURNING id"),
                                {"n": f"Usuario Ficticio {self.prox}",
                                 "e": f"u{self.prox}-4d4a@example.invalid"}).scalar_one()

    def vinculo(self, empresa, ativo=True, papel="USUARIO"):
        uid = self.usuario()
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO empresa_usuarios (empresa_id, usuario_id, papel, ativo)"
                              " VALUES (:e, :u, :p, :a)"), {"e": empresa, "u": uid, "p": papel, "a": ativo})
        return uid

    def ativos(self, empresa):
        with self.engine.connect() as conn:
            return conn.execute(text(
                "SELECT count(*) FROM empresa_usuarios eu JOIN usuarios u ON u.id = eu.usuario_id"
                " WHERE eu.empresa_id = :e AND eu.ativo AND u.status = 'ATIVO'"), {"e": empresa}).scalar_one()

    def total(self, empresa):
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT count(*) FROM empresa_usuarios WHERE empresa_id = :e"),
                                {"e": empresa}).scalar_one()

    def aguardando_trava(self, pid):
        fim = time.monotonic() + TIMEOUT_S
        while time.monotonic() < fim:
            with self.engine.connect() as conn:
                linha = conn.execute(text("SELECT wait_event_type, query FROM pg_stat_activity WHERE pid = :p"),
                                     {"p": pid}).one_or_none()
            if linha and linha[0] == "Lock":
                return linha[1]
            time.sleep(0.05)
        return None

    def disputar(self, op_a, op_b, limite_valor, empresa_b_independente=False):
        """A segura a trava (no resolvedor) ate B estar bloqueado no FOR UPDATE; depois libera A.

        op(sessao, resolver). Com empresa_b_independente, B nao deve esperar A.
        """
        a_tem_trava, liberar, b_resolveu, b_pid_pronto = (threading.Event() for _ in range(4))
        r = {"pid_b": None}

        def res_a(sessao, empresa_id):
            a_tem_trava.set()
            if not liberar.wait(TIMEOUT_S):
                return None
            return limite_valor

        def res_b(sessao, empresa_id):
            b_resolveu.set()
            return limite_valor

        def trabalhador(chave, op, resolvedor):
            sessao = Session(self.engine)
            try:
                if chave == "b":
                    r["pid_b"] = sessao.execute(text("SELECT pg_backend_pid()")).scalar_one()
                    b_pid_pronto.set()
                op(sessao, resolvedor)
                sessao.commit()
                r[chave] = "OK"
            except Exception as exc:
                sessao.rollback()
                r[chave] = exc
            finally:
                sessao.close()

        ta = threading.Thread(target=trabalhador, args=("a", op_a, res_a), daemon=True)
        tb = threading.Thread(target=trabalhador, args=("b", op_b, res_b), daemon=True)
        ta.start()
        self.assertTrue(a_tem_trava.wait(TIMEOUT_S), "A nao adquiriu a trava")
        tb.start()
        self.assertTrue(b_pid_pronto.wait(TIMEOUT_S))
        if empresa_b_independente:
            tb.join(TIMEOUT_S)
            self.assertFalse(tb.is_alive(), "B (outra empresa) ficou preso pela trava de A")
            r["b_terminou_antes_de_liberar_a"] = True
        else:
            consulta = self.aguardando_trava(r["pid_b"])
            self.assertIsNotNone(consulta, "B nao ficou aguardando trava")
            self.assertIn("FOR UPDATE", consulta.upper())
            self.assertFalse(b_resolveu.is_set(), "B avancou ate o resolvedor sem a trava")
            r["consulta_bloqueada"] = consulta
        liberar.set()
        ta.join(TIMEOUT_S)
        tb.join(TIMEOUT_S)
        self.assertFalse(ta.is_alive() or tb.is_alive(), "operacao concorrente excedeu o timeout")
        return r


class ConcorrenciaTests(Base):
    def test_criacao_disputando_ultima_vaga(self):
        emp = self.empresa()
        self.vinculo(emp, papel="OWNER")
        ua, ub = self.usuario(), self.usuario()
        r = self.disputar(
            lambda s, res: ms.link_user_to_company(s, usuario_id=ua, empresa_id=emp, papel="USUARIO",
                                                   resolver_limite=res),
            lambda s, res: ms.link_user_to_company(s, usuario_id=ub, empresa_id=emp, papel="USUARIO",
                                                   resolver_limite=res),
            2)
        self.assertEqual(r["a"], "OK")
        self.assertIsInstance(r["b"], ms.VagaIndisponivelError)
        self.assertEqual(r["b"].decisao.situacao, S.LIMITE_ATINGIDO)
        self.assertEqual(r["b"].decisao.usuarios_ativos, 2)
        self.assertEqual(self.ativos(emp), 2)
        self.assertEqual(self.total(emp), 2)
        self.assertTrue(any("FOR UPDATE" in s.upper() and "empresas" in s for s in self.sql))

    def test_reativacao_disputando_ultima_vaga(self):
        emp = self.empresa()
        self.vinculo(emp, papel="OWNER")
        ua, ub = self.vinculo(emp, ativo=False), self.vinculo(emp, ativo=False)
        r = self.disputar(
            lambda s, res: ms.reactivate_user_company_link(s, usuario_id=ua, empresa_id=emp, resolver_limite=res),
            lambda s, res: ms.reactivate_user_company_link(s, usuario_id=ub, empresa_id=emp, resolver_limite=res),
            2)
        self.assertEqual(r["a"], "OK")
        self.assertIsInstance(r["b"], ms.VagaIndisponivelError)
        self.assertEqual(r["b"].decisao.situacao, S.LIMITE_ATINGIDO)
        self.assertEqual(self.ativos(emp), 2)
        self.assertEqual(self.total(emp), 3)

    def test_empresas_diferentes_nao_compartilham_limite_nem_trava(self):
        e1, e2 = self.empresa(), self.empresa()
        self.vinculo(e1, papel="OWNER")
        self.vinculo(e2, papel="OWNER")
        ua, ub = self.usuario(), self.usuario()
        r = self.disputar(
            lambda s, res: ms.link_user_to_company(s, usuario_id=ua, empresa_id=e1, papel="USUARIO",
                                                   resolver_limite=res),
            lambda s, res: ms.link_user_to_company(s, usuario_id=ub, empresa_id=e2, papel="USUARIO",
                                                   resolver_limite=res),
            2, empresa_b_independente=True)
        self.assertEqual((r["a"], r["b"]), ("OK", "OK"))
        self.assertEqual((self.ativos(e1), self.ativos(e2)), (2, 2))

    def test_rollback_libera_trava_sem_vinculo_parcial(self):
        emp = self.empresa()
        self.vinculo(emp, papel="OWNER")
        ua, ub = self.usuario(), self.usuario()

        def falha_apos_gravar(s, res):
            ms.link_user_to_company(s, usuario_id=ua, empresa_id=emp, papel="USUARIO", resolver_limite=res)
            s.flush()
            raise RuntimeError("falha simulada apos gravar")

        r = self.disputar(
            falha_apos_gravar,
            lambda s, res: ms.link_user_to_company(s, usuario_id=ub, empresa_id=emp, papel="USUARIO",
                                                   resolver_limite=res),
            2)
        self.assertIsInstance(r["a"], RuntimeError)
        self.assertEqual(r["b"], "OK")
        with self.engine.connect() as conn:
            ligados = {x[0] for x in conn.execute(text("SELECT usuario_id FROM empresa_usuarios"
                                                       " WHERE empresa_id = :e"), {"e": emp})}
        self.assertNotIn(ua, ligados)
        self.assertIn(ub, ligados)
        self.assertEqual(self.ativos(emp), 2)

    def test_servico_nao_faz_commit_e_a_trava_persiste_ate_o_rollback(self):
        emp = self.empresa()
        self.vinculo(emp, papel="OWNER")
        novo = self.usuario()
        sessao = Session(self.engine)
        self.addCleanup(sessao.close)
        ms.link_user_to_company(sessao, usuario_id=novo, empresa_id=emp, papel="USUARIO", resolver_limite=limite(3))
        sessao.flush()
        self.assertEqual(self.total(emp), 1)  # linha gravada na transacao, mas nao confirmada
        with self.engine.connect() as outra:
            with self.assertRaises(OperationalError):
                outra.execute(text("SELECT id FROM empresas WHERE id = :e FOR UPDATE NOWAIT"), {"e": emp})
        sessao.rollback()
        with self.engine.connect() as outra:
            self.assertEqual(outra.execute(text("SELECT id FROM empresas WHERE id = :e FOR UPDATE NOWAIT"),
                                           {"e": emp}).scalar_one(), emp)
        self.assertEqual(self.total(emp), 1)


class RegrasTests(Base):
    def test_empresa_acima_do_limite_nao_perde_usuarios(self):
        emp = self.empresa()
        for _ in range(3):
            self.vinculo(emp)
        inativo = self.vinculo(emp, ativo=False)
        novo = self.usuario()
        with Session(self.engine) as s:
            with self.assertRaises(ms.VagaIndisponivelError) as c1:
                ms.link_user_to_company(s, usuario_id=novo, empresa_id=emp, papel="USUARIO",
                                        resolver_limite=limite(2))
            s.rollback()
            with self.assertRaises(ms.VagaIndisponivelError) as c2:
                ms.reactivate_user_company_link(s, usuario_id=inativo, empresa_id=emp, resolver_limite=limite(2))
            s.rollback()
        self.assertEqual(c1.exception.decisao.situacao, S.LIMITE_EXCEDIDO)
        self.assertEqual(c2.exception.decisao.situacao, S.LIMITE_EXCEDIDO)
        self.assertEqual((self.ativos(emp), self.total(emp)), (3, 4))

    def test_limite_desconhecido_nao_autoriza(self):
        emp = self.empresa()
        inativo = self.vinculo(emp, ativo=False)
        novo = self.usuario()
        for resolvedor in (limite(None), limite("2"), limite(True), limite(-1)):
            with Session(self.engine) as s:
                with self.assertRaises(ms.VagaIndisponivelError) as c1:
                    ms.link_user_to_company(s, usuario_id=novo, empresa_id=emp, papel="USUARIO",
                                            resolver_limite=resolvedor)
                s.rollback()
                with self.assertRaises(ms.VagaIndisponivelError) as c2:
                    ms.reactivate_user_company_link(s, usuario_id=inativo, empresa_id=emp,
                                                    resolver_limite=resolvedor)
                s.rollback()
            self.assertEqual(c1.exception.decisao.situacao, S.LIMITE_DESCONHECIDO)
            self.assertEqual(c2.exception.decisao.situacao, S.LIMITE_DESCONHECIDO)
        self.assertEqual((self.ativos(emp), self.total(emp)), (0, 1))

    def test_sem_resolvedor_preserva_comportamento_anterior(self):
        emp = self.empresa()
        for _ in range(4):
            self.vinculo(emp)
        inativo = self.vinculo(emp, ativo=False)
        novo = self.usuario()
        self.sql.clear()
        with Session(self.engine) as s:
            ms.link_user_to_company(s, usuario_id=novo, empresa_id=emp, papel="ADMIN")
            ms.reactivate_user_company_link(s, usuario_id=inativo, empresa_id=emp)
            s.commit()
        self.assertFalse(any("FOR UPDATE" in q.upper() for q in self.sql))
        self.assertEqual(self.ativos(emp), 6)

    def test_contagem_ignora_usuario_inativo_no_postgres(self):
        emp = self.empresa()
        uid = self.vinculo(emp)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE usuarios SET status = 'INATIVO' WHERE id = :u"), {"u": uid})
        self.vinculo(emp)
        with Session(self.engine) as s:
            self.assertEqual(contar_usuarios_ativos(s, emp), 1)
            s.rollback()


if __name__ == "__main__":
    unittest.main()
