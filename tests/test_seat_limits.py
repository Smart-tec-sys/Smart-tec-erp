"""Testes da 4D.2: contagem e verificacao de vagas. SQLite em memoria e mocks."""
import unittest
from unittest import mock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth import seat_limits as sl
from app.auth.seat_limits import SituacaoVaga as S

# Planos FICTICIOS: nomes e limites apenas de teste, sem relacao com IDs Wix ou codigos reais.
LIMITES_FICTICIOS = {
    "PLANO_FICTICIO_VISITA": 2,
    "PLANO_FICTICIO_ESSENCIAL": 2,
    "PLANO_FICTICIO_PROFISSIONAL": 3,
    "PLANO_FICTICIO_PRIME": 4,
}


def resolvedor(plano_por_empresa):
    def _r(sessao, empresa_id):
        return LIMITES_FICTICIOS.get(plano_por_empresa.get(empresa_id))
    return _r


class Base(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        with self.engine.begin() as c:
            c.execute(text("CREATE TABLE empresas (id INTEGER PRIMARY KEY, status TEXT)"))
            c.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, status TEXT)"))
            c.execute(text("CREATE TABLE plataforma_equipe (id INTEGER PRIMARY KEY, usuario_id INTEGER)"))
            c.execute(text("CREATE TABLE empresa_usuarios (id INTEGER PRIMARY KEY, empresa_id INTEGER,"
                           " usuario_id INTEGER, papel TEXT, ativo BOOLEAN, UNIQUE (empresa_id, usuario_id))"))
            c.execute(text("INSERT INTO empresas VALUES (1,'ATIVA'),(2,'ATIVA'),(3,'INATIVA')"))
        self.sessao = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.sessao.close)
        self.prox = 0

    def usuario(self, status="ATIVO"):
        self.prox += 1
        self.sessao.execute(text("INSERT INTO usuarios VALUES (:i, :s)"), {"i": self.prox, "s": status})
        return self.prox

    def vinculo(self, empresa=1, papel="USUARIO", ativo=True, status="ATIVO", usuario=None):
        usuario = usuario or self.usuario(status)
        self.sessao.execute(text("INSERT INTO empresa_usuarios (empresa_id, usuario_id, papel, ativo)"
                                 " VALUES (:e,:u,:p,:a)"), {"e": empresa, "u": usuario, "p": papel, "a": ativo})
        return usuario

    def vagas(self, plano, empresa=1):
        return sl.verificar_vaga(self.sessao, empresa, resolver_limite=resolvedor({empresa: plano}))

    def contagem_total(self):
        return {t: self.sessao.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
                for t in ("empresas", "usuarios", "empresa_usuarios", "plataforma_equipe")}


class ContagemTest(Base):
    def test_tres_papeis_contam(self):
        for papel in ("OWNER", "ADMIN", "USUARIO"):
            self.vinculo(papel=papel)
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 3)

    def test_vinculo_inativo_nao_conta(self):
        self.vinculo()
        self.vinculo(ativo=False)
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 1)

    def test_usuario_inativo_nao_conta(self):
        self.vinculo()
        self.vinculo(status="INATIVO")
        self.vinculo(status="BLOQUEADO")
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 1)

    def test_equipe_da_plataforma_sem_vinculo_nao_conta(self):
        u = self.usuario()
        self.sessao.execute(text("INSERT INTO plataforma_equipe (usuario_id) VALUES (:u)"), {"u": u})
        self.vinculo()
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 1)

    def test_usuario_com_vinculo_conta_uma_vez_e_duplicata_e_impossivel(self):
        u = self.vinculo(papel="OWNER")
        with self.assertRaises(Exception):
            with self.sessao.begin_nested():
                self.vinculo(papel="ADMIN", usuario=u)
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 1)

    def test_usuario_em_duas_empresas_conta_em_cada_uma(self):
        u = self.vinculo(empresa=1)
        self.vinculo(empresa=2, usuario=u)
        self.assertEqual((sl.contar_usuarios_ativos(self.sessao, 1), sl.contar_usuarios_ativos(self.sessao, 2)), (1, 1))

    def test_isolamento_entre_empresas(self):
        self.vinculo(empresa=1)
        self.vinculo(empresa=2)
        self.vinculo(empresa=2)
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 1)

    def test_empresa_id_invalido(self):
        for v in (0, -1, True, "1", None):
            with self.assertRaises(ValueError):
                sl.contar_usuarios_ativos(self.sessao, v)


class DecisaoTest(Base):
    def test_limites_2_2_3_4(self):
        for plano, limite in LIMITES_FICTICIOS.items():
            with self.subTest(plano=plano):
                self.setUp()
                for _ in range(limite - 1):
                    self.vinculo()
                d = self.vagas(plano)
                self.assertEqual((d.situacao, d.usuarios_ativos, d.limite), (S.VAGA_DISPONIVEL, limite - 1, limite))
                self.assertTrue(d.permite_expansao)
                self.vinculo()
                d = self.vagas(plano)
                self.assertEqual(d.situacao, S.LIMITE_ATINGIDO)
                self.assertFalse(d.permite_expansao)
                self.vinculo()
                d = self.vagas(plano)
                self.assertEqual((d.situacao, d.usuarios_ativos), (S.LIMITE_EXCEDIDO, limite + 1))
                self.assertFalse(d.permite_expansao)

    def test_empresa_vazia_tem_vaga(self):
        self.assertEqual(self.vagas("PLANO_FICTICIO_VISITA").situacao, S.VAGA_DISPONIVEL)

    def test_limite_desconhecido_nunca_autoriza(self):
        self.vinculo()
        for r in (lambda s, e: None, lambda s, e: -1, lambda s, e: True, lambda s, e: "2",
                  lambda s, e: 2.0, lambda s, e: (_ for _ in ()).throw(RuntimeError("falha"))):
            d = sl.verificar_vaga(self.sessao, 1, resolver_limite=r)
            self.assertEqual(d.situacao, S.LIMITE_DESCONHECIDO)
            self.assertFalse(d.permite_expansao)
            self.assertIsNone(d.limite)
        self.assertEqual(self.vagas("PLANO_QUE_NAO_EXISTE").situacao, S.LIMITE_DESCONHECIDO)
        self.assertEqual(self.vagas(None).situacao, S.LIMITE_DESCONHECIDO)

    def test_limite_zero_e_valido(self):
        d = sl.verificar_vaga(self.sessao, 1, resolver_limite=lambda s, e: 0)
        self.assertEqual(d.situacao, S.LIMITE_ATINGIDO)

    def test_empresa_inexistente_ou_inativa(self):
        for empresa in (99, 3):
            d = self.vagas("PLANO_FICTICIO_PRIME", empresa)
            self.assertEqual(d.situacao, S.EMPRESA_INDISPONIVEL)
            self.assertFalse(d.permite_expansao)
        for v in (0, -1, True, "1", None):
            self.assertEqual(sl.verificar_vaga(self.sessao, v, resolver_limite=lambda s, e: 4).situacao,
                             S.EMPRESA_INDISPONIVEL)
        self.assertEqual(sl.verificar_vaga(self.sessao, 1, resolver_limite=None).situacao, S.EMPRESA_INDISPONIVEL)

    def test_empresa_indisponivel_nao_chama_resolvedor(self):
        r = mock.Mock(return_value=4)
        sl.verificar_vaga(self.sessao, 99, resolver_limite=r)
        r.assert_not_called()

    def test_vinculos_atuais_acima_do_limite_nao_sao_alterados(self):
        for _ in range(4):
            self.vinculo()
        antes = self.contagem_total()
        self.assertEqual(self.vagas("PLANO_FICTICIO_VISITA").situacao, S.LIMITE_EXCEDIDO)
        self.assertEqual(antes, self.contagem_total())
        self.assertEqual(sl.contar_usuarios_ativos(self.sessao, 1), 4)


class TravaETransacaoTest(unittest.TestCase):
    def sessao_falsa(self, dialeto, linhas):
        sessao = mock.MagicMock()
        sessao.get_bind.return_value.dialect.name = dialeto
        chamadas = []

        def execute(stmt, params=None):
            sql = str(stmt)
            chamadas.append(sql)
            r = mock.MagicMock()
            r.first.return_value = linhas
            r.scalar_one.return_value = 1
            return r
        sessao.execute.side_effect = execute
        return sessao, chamadas

    def test_postgresql_trava_empresa_antes_de_contar(self):
        sessao, chamadas = self.sessao_falsa("postgresql", (1, "ATIVA"))
        resolvido = []
        sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: resolvido.append(len(chamadas)) or 3)
        self.assertEqual(len(chamadas), 2)
        self.assertTrue(chamadas[0].rstrip().endswith("FOR UPDATE"))
        self.assertIn("FROM empresas", chamadas[0])
        self.assertIn("COUNT(*)", chamadas[1])
        self.assertNotIn("FOR UPDATE", chamadas[1])
        self.assertEqual(resolvido, [2])

    def test_dialeto_desconhecido_exige_trava(self):
        sessao, chamadas = self.sessao_falsa("outro", (1, "ATIVA"))
        sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: 3)
        self.assertTrue(chamadas[0].rstrip().endswith("FOR UPDATE"))

    def test_sqlite_nao_emite_for_update(self):
        sessao, chamadas = self.sessao_falsa("sqlite", (1, "ATIVA"))
        sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: 3)
        self.assertNotIn("FOR UPDATE", chamadas[0])

    def test_empresa_inativa_trava_mas_nao_conta(self):
        sessao, chamadas = self.sessao_falsa("postgresql", (1, "INATIVA"))
        sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: 3)
        self.assertEqual(len(chamadas), 1)

    def test_sem_commit_rollback_flush_ou_mutacao(self):
        sessao, chamadas = self.sessao_falsa("postgresql", (1, "ATIVA"))
        sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: 3)
        for nome in ("commit", "rollback", "flush", "add", "delete", "begin", "close", "merge"):
            getattr(sessao, nome).assert_not_called()
        for sql in chamadas:
            self.assertRegex(sql.lstrip().upper(), r"^SELECT")
            for proibido in ("INSERT", "UPDATE ", "DELETE ", "ALTER", "DROP"):
                self.assertNotIn(proibido, sql.upper())

    def test_transacao_do_chamador_permanece_aberta(self):
        engine = create_engine("sqlite://")
        with engine.begin() as c:
            c.execute(text("CREATE TABLE empresas (id INTEGER, status TEXT)"))
            c.execute(text("CREATE TABLE usuarios (id INTEGER, status TEXT)"))
            c.execute(text("CREATE TABLE empresa_usuarios (empresa_id INTEGER, usuario_id INTEGER, ativo BOOLEAN)"))
            c.execute(text("INSERT INTO empresas VALUES (1,'ATIVA')"))
        with Session(engine) as sessao:
            sl.verificar_vaga(sessao, 1, resolver_limite=lambda s, e: 2)
            self.assertTrue(sessao.in_transaction())
        engine.dispose()


class IsolamentoTest(unittest.TestCase):
    def test_fonte_isolada(self):
        import pathlib
        fonte = pathlib.Path(sl.__file__).read_text(encoding="utf-8")
        for proibido in ("commit(", "INSERT", "UPDATE ", "DELETE ", "limite_usuarios", "app.models", "app.database",
                         "os." + "environ", "getenv", "wix", "Wix", "fastapi", "HTTPException"):
            self.assertNotIn(proibido, fonte)

    def test_fluxos_existentes_nao_referenciam_o_modulo(self):
        import pathlib
        raiz = pathlib.Path(sl.__file__).resolve().parents[2]
        for arq in ("app/auth/tenant_resolver.py", "app/routes/admin.py",
                    "app/routes/auth.py", "app/main.py"):
            self.assertNotIn("seat_limits", (raiz / arq).read_text(encoding="utf-8", errors="ignore"))


if __name__ == "__main__":
    unittest.main()