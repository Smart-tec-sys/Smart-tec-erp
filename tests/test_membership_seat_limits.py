"""Testes da 4D.3: vagas integradas ao servico de vinculos. SQLite em memoria, sem banco real."""
import unittest
from unittest import mock

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.auth import membership_service as ms
from app.auth.seat_limits import SituacaoVaga as S
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB

# Limites FICTICIOS, sem relacao com planos Wix ou planos_saas.
def limite(valor):
    return lambda sessao, empresa_id: valor


class Base(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        for modelo in (EmpresaDB, UsuarioDB, EmpresaUsuarioDB):
            modelo.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.db.add(EmpresaDB(id=1, nome="E1", slug="e1", status="ATIVA"))
        self.db.add(EmpresaDB(id=2, nome="E2", slug="e2", status="ATIVA"))
        self.db.flush()
        self.sql = []
        event.listen(self.engine, "before_cursor_execute",
                     lambda c, cur, stmt, *a: self.sql.append(stmt))

    def usuario(self, status="ATIVO"):
        u = UsuarioDB(nome="u", email="u@example.test", status=status)
        self.db.add(u)
        self.db.flush()
        return u.id

    def vinculo(self, empresa=1, ativo=True, papel="USUARIO"):
        uid = self.usuario()
        self.db.add(EmpresaUsuarioDB(empresa_id=empresa, usuario_id=uid, papel=papel, ativo=ativo))
        self.db.flush()
        return uid

    def ocupar(self, n, empresa=1):
        for papel in ["OWNER", "ADMIN", "USUARIO", "USUARIO"][:n]:
            self.vinculo(empresa, papel=papel)

    def consultou_limite(self):
        return any("empresa_usuarios" in s and "count" in s.lower() for s in self.sql)


class CriacaoTests(Base):
    def test_sem_protecao_cria_como_antes_e_sem_consulta_de_limite(self):
        self.ocupar(4)
        novo = self.usuario()
        self.sql.clear()
        v = ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="usuario")
        self.assertTrue(v.ativo)
        self.assertEqual(v.papel, "USUARIO")
        self.assertFalse(self.consultou_limite())

    def test_sem_protecao_nao_chama_verificador(self):
        novo = self.usuario()
        with mock.patch.object(ms, "verificar_vaga") as vv:
            ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="ADMIN")
        vv.assert_not_called()

    def test_com_vaga(self):
        self.ocupar(1)
        novo = self.usuario()
        v = ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                    resolver_limite=limite(2))
        self.assertIn(v, self.db.new)

    def test_negada_no_limite(self):
        self.ocupar(2)
        novo = self.usuario()
        with self.assertRaises(ms.VagaIndisponivelError) as ctx:
            ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                    resolver_limite=limite(2))
        self.assertEqual(ctx.exception.decisao.situacao, S.LIMITE_ATINGIDO)
        self.assertEqual(len(self.db.new), 0)

    def test_negada_acima_do_limite(self):
        self.ocupar(3)
        novo = self.usuario()
        with self.assertRaises(ms.VagaIndisponivelError) as ctx:
            ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                    resolver_limite=limite(2))
        self.assertEqual(ctx.exception.decisao.situacao, S.LIMITE_EXCEDIDO)

    def test_limite_desconhecido_nao_autoriza(self):
        novo = self.usuario()
        for r in (limite(None), limite("3"), limite(True), mock.Mock(side_effect=RuntimeError("x"))):
            with self.assertRaises(ms.VagaIndisponivelError) as ctx:
                ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                        resolver_limite=r)
            self.assertEqual(ctx.exception.decisao.situacao, S.LIMITE_DESCONHECIDO)
        self.assertEqual(len(self.db.new), 0)

    def test_erros_existentes_preservados_com_e_sem_protecao(self):
        ok = self.usuario()
        inativo = self.usuario("INATIVO")
        self.vinculo(1)
        casos = [
            (dict(usuario_id=ok, empresa_id=1, papel="X"), "papel inválido"),
            (dict(usuario_id=999, empresa_id=1, papel="ADMIN"), "usuário não encontrado"),
            (dict(usuario_id=inativo, empresa_id=1, papel="ADMIN"), "usuário inativo"),
            (dict(usuario_id=ok, empresa_id=999, papel="ADMIN"), "empresa não encontrada"),
        ]
        for resolver in (None, limite(10)):
            for kwargs, msg in casos:
                with self.assertRaisesRegex(ValueError, msg):
                    ms.link_user_to_company(self.db, resolver_limite=resolver, **kwargs)
        existente = self.db.query(EmpresaUsuarioDB).first().usuario_id
        with self.assertRaisesRegex(ValueError, "já possui vínculo"):
            ms.link_user_to_company(self.db, usuario_id=existente, empresa_id=1, papel="ADMIN",
                                    resolver_limite=limite(0))

    def test_erro_de_vinculo_duplicado_vem_antes_da_verificacao_de_vaga(self):
        uid = self.vinculo(1)
        with mock.patch.object(ms, "verificar_vaga") as vv:
            with self.assertRaisesRegex(ValueError, "já possui vínculo"):
                ms.link_user_to_company(self.db, usuario_id=uid, empresa_id=1, papel="ADMIN",
                                        resolver_limite=limite(10))
        vv.assert_not_called()

    def test_trava_antes_da_alteracao_e_mesma_transacao(self):
        self.ocupar(1)
        novo = self.usuario()
        visto = {}
        real = ms.verificar_vaga

        def espiao(sessao, empresa_id, **kw):
            visto["sessao"] = sessao
            visto["pendentes"] = len(sessao.new)
            return real(sessao, empresa_id, **kw)

        with mock.patch.object(ms, "verificar_vaga", side_effect=espiao):
            ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                    resolver_limite=limite(2))
        self.assertIs(visto["sessao"], self.db)
        self.assertEqual(visto["pendentes"], 0)
        self.assertEqual(len(self.db.new), 1)

    def test_sem_commit_ou_rollback_internos(self):
        self.ocupar(1)
        novo = self.usuario()
        with mock.patch.object(Session, "commit", side_effect=AssertionError), \
                mock.patch.object(Session, "rollback", side_effect=AssertionError):
            ms.link_user_to_company(self.db, usuario_id=novo, empresa_id=1, papel="USUARIO",
                                    resolver_limite=limite(2))
            with self.assertRaises(ms.VagaIndisponivelError):
                ms.link_user_to_company(self.db, usuario_id=self.usuario(), empresa_id=1,
                                        papel="USUARIO", resolver_limite=limite(0))


class ReativacaoTests(Base):
    def inativo(self, empresa=1):
        return self.vinculo(empresa, ativo=False)

    def test_reativa_com_vaga(self):
        self.ocupar(1)
        uid = self.inativo()
        v = ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                            resolver_limite=limite(2))
        self.assertTrue(v.ativo)

    def test_reativa_sem_protecao_sem_consulta_de_limite(self):
        self.ocupar(4)
        uid = self.inativo()
        self.sql.clear()
        with mock.patch.object(ms, "verificar_vaga") as vv:
            v = ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1)
        vv.assert_not_called()
        self.assertTrue(v.ativo)
        self.assertFalse(self.consultou_limite())

    def test_reativa_sem_vaga(self):
        self.ocupar(2)
        uid = self.inativo()
        with self.assertRaises(ms.VagaIndisponivelError):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                            resolver_limite=limite(2))
        vinc = self.db.query(EmpresaUsuarioDB).filter_by(usuario_id=uid).one()
        self.assertFalse(vinc.ativo)

    def test_limite_desconhecido_nao_reativa(self):
        uid = self.inativo()
        with self.assertRaises(ms.VagaIndisponivelError):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                            resolver_limite=limite(None))
        self.assertFalse(self.db.query(EmpresaUsuarioDB).filter_by(usuario_id=uid).one().ativo)

    def test_vinculo_ja_ativo_nao_consome_vaga_nem_consulta(self):
        self.ocupar(2)
        uid = self.vinculo(1)
        with mock.patch.object(ms, "verificar_vaga") as vv:
            v = ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                                resolver_limite=limite(2))
        vv.assert_not_called()
        self.assertTrue(v.ativo)

    def test_nao_desativa_existentes_acima_do_limite(self):
        self.ocupar(4)
        uid = self.inativo()
        with self.assertRaises(ms.VagaIndisponivelError):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                            resolver_limite=limite(2))
        ativos = self.db.query(EmpresaUsuarioDB).filter_by(empresa_id=1, ativo=True).count()
        self.assertEqual(ativos, 4)

    def test_erros(self):
        uid = self.inativo()
        with self.assertRaisesRegex(ValueError, "vínculo não encontrado"):
            ms.reactivate_user_company_link(self.db, usuario_id=999, empresa_id=1)
        self.db.query(UsuarioDB).filter_by(id=uid).update({"status": "INATIVO"})
        with self.assertRaisesRegex(ValueError, "usuário inativo"):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1)
        self.db.query(UsuarioDB).filter_by(id=uid).update({"status": "ATIVO"})
        self.db.query(EmpresaDB).filter_by(id=1).update({"status": "INATIVA"})
        with self.assertRaisesRegex(ValueError, "empresa inativa"):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1)

    def test_trava_antes_da_alteracao_e_sem_commit(self):
        uid = self.inativo()
        visto = {}
        real = ms.verificar_vaga

        def espiao(sessao, empresa_id, **kw):
            visto["sessao"] = sessao
            visto["ativo"] = sessao.query(EmpresaUsuarioDB).filter_by(usuario_id=uid).one().ativo
            return real(sessao, empresa_id, **kw)

        with mock.patch.object(ms, "verificar_vaga", side_effect=espiao), \
                mock.patch.object(Session, "commit", side_effect=AssertionError):
            ms.reactivate_user_company_link(self.db, usuario_id=uid, empresa_id=1,
                                            resolver_limite=limite(2))
        self.assertIs(visto["sessao"], self.db)
        self.assertFalse(visto["ativo"])


class CompatibilidadeTests(unittest.TestCase):
    def test_assinaturas_existentes_e_padrao_desligado(self):
        import inspect
        for f in (ms.link_user_to_company, ms.reactivate_user_company_link):
            self.assertIsNone(inspect.signature(f).parameters["resolver_limite"].default)
        self.assertTrue(issubclass(ms.VagaIndisponivelError, ValueError))

    def test_login_e_rotas_nao_referenciam_reativacao_nem_vagas(self):
        from pathlib import Path
        raiz = Path(__file__).resolve().parents[1] / "app"
        for rel in ("auth/tenant_resolver.py", "main.py", "routes/auth.py", "routes/admin.py"):
            arq = raiz / rel
            if arq.exists():
                texto = arq.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("reactivate_user_company_link", texto, rel)
                self.assertNotIn("resolver_limite", texto, rel)


if __name__ == "__main__":
    unittest.main()
