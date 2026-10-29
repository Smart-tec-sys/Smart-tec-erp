import ast
import pathlib
import sqlite3
import unittest
from unittest import mock

from sqlalchemy import create_engine, text
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app.tenant import commercial_observer_pool as mod
from app.tenant.commercial_observer_pool import (
    ConfiguracaoPool,
    PoolObservacaoErro,
    criar_pool_observacao,
)

SEGREDO = "senha-super-secreta"
URL = f"postgresql+psycopg2://usuario:{SEGREDO}@host-inexistente.invalid:5432/erp"


class MotorFalso:
    def __init__(self, url, kwargs):
        self.url, self.kwargs, self.descartado = url, kwargs, 0

    def dispose(self):
        self.descartado += 1


class Fabrica:
    def __init__(self, falha=False):
        self.chamadas, self.motores, self.falha = 0, [], falha
        unittest.addModuleCleanup(self.descartar)

    def descartar(self):
        for m in self.motores:
            m.dispose()

    def __call__(self, url, **kwargs):
        self.chamadas += 1
        if self.falha:
            raise RuntimeError(f"nao conectou em {url}")
        motor = create_engine("sqlite://", creator=lambda: sqlite3.connect(":memory:", check_same_thread=False),
                              **{k: v for k, v in kwargs.items() if k in
                                 ("poolclass", "pool_size", "max_overflow", "pool_timeout", "pool_recycle", "pool_pre_ping")})
        motor.kwargs = kwargs
        self.motores.append(motor)
        return motor


class ConfiguracaoTest(unittest.TestCase):
    def test_padrao_conservador(self):
        c = ConfiguracaoPool()
        self.assertEqual((c.tamanho, c.excesso_maximo), (2, 0))
        self.assertLessEqual(c.espera_conexao_s, 1.0)
        self.assertTrue(c.verificar_conexao)
        self.assertLessEqual(c.reciclagem_s, 300)

    def test_valores_invalidos_rejeitados(self):
        for kw in ({"tamanho": 0}, {"tamanho": 99}, {"tamanho": True}, {"excesso_maximo": -1},
                   {"excesso_maximo": 50}, {"espera_conexao_s": 0}, {"espera_conexao_s": 60},
                   {"espera_conexao_s": "1"}, {"reciclagem_s": 1}, {"verificar_conexao": 1},
                   {"timeout_conexao_s": 0}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                ConfiguracaoPool(**kw)

    def test_entradas_invalidas_do_pool(self):
        for url in (None, "", "  "):
            with self.assertRaises(PoolObservacaoErro):
                criar_pool_observacao(url)
        with self.assertRaises(PoolObservacaoErro):
            criar_pool_observacao(URL, {"tamanho": 1})


class CicloDeVidaTest(unittest.TestCase):
    def test_inicializacao_sem_conexao(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        self.assertFalse(pool.iniciado)
        self.assertEqual(f.chamadas, 0)

    def test_engine_criado_so_no_primeiro_uso_sem_conectar(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        s = pool.session_factory()
        self.assertEqual(f.chamadas, 1)
        self.assertEqual(f.motores[0].pool.checkedout(), 0)
        s.close()

    def test_parametros_do_pool_repassados(self):
        f = Fabrica()
        cfg = ConfiguracaoPool(tamanho=3, excesso_maximo=1, espera_conexao_s=0.5, reciclagem_s=120)
        pool = criar_pool_observacao(URL, cfg, engine_factory=f)
        pool.session_factory().close()
        k = f.motores[0].kwargs
        self.assertEqual((k["pool_size"], k["max_overflow"], k["pool_timeout"], k["pool_recycle"]),
                         (3, 1, 0.5, 120))
        self.assertTrue(k["pool_pre_ping"])
        self.assertEqual(k["connect_args"], {"connect_timeout": 3})
        self.assertFalse(k["echo"])
        self.assertTrue(k["hide_parameters"])

    def test_fechar_descarta_e_impede_novo_uso(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        pool.session_factory().close()
        motor = f.motores[0]
        with mock.patch.object(motor, "dispose", wraps=motor.dispose) as d:
            pool.fechar()
            pool.fechar()
            d.assert_called_once()
        self.assertTrue(pool.fechado)
        with self.assertRaises(PoolObservacaoErro):
            pool.session_factory()
        self.assertEqual(f.chamadas, 1)

    def test_fechar_sem_uso_nao_cria_engine(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        pool.fechar()
        self.assertEqual(f.chamadas, 0)

    def test_erro_ao_descartar_nao_propaga(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        pool.session_factory().close()
        with mock.patch.object(f.motores[0], "dispose", side_effect=RuntimeError("x")):
            pool.fechar()


class FalhasTest(unittest.TestCase):
    def test_falha_de_criacao_do_engine_sem_credenciais(self):
        pool = criar_pool_observacao(URL, engine_factory=Fabrica(falha=True))
        with self.assertRaises(PoolObservacaoErro) as ctx:
            pool.session_factory()
        self.assertNotIn(SEGREDO, str(ctx.exception))
        self.assertNotIn("host-inexistente", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)
        self.assertFalse(pool.iniciado)

    def test_esgotamento_do_pool_falha_rapido(self):
        f = Fabrica()
        cfg = ConfiguracaoPool(tamanho=1, excesso_maximo=0, espera_conexao_s=0.05)
        pool = criar_pool_observacao(URL, cfg, engine_factory=f)
        s1, s2 = pool.session_factory(), pool.session_factory()
        try:
            s1.execute(text("select 1"))
            with self.assertRaises(PoolTimeout):
                s2.execute(text("select 1"))
        finally:
            s1.close()
            s2.close()
        s3 = pool.session_factory()
        try:
            self.assertEqual(s3.execute(text("select 1")).scalar(), 1)
        finally:
            s3.close()
        self.assertEqual(f.motores[0].pool.checkedout(), 0)

    def test_banco_indisponivel_com_engine_real_nao_conecta_no_inicio(self):
        pool = criar_pool_observacao(URL)
        try:
            self.assertFalse(pool.iniciado)
            try:
                s = pool.session_factory()
            except Exception:
                self.skipTest("driver indisponivel")
            self.assertEqual(pool._engine.pool.checkedout(), 0)
            s.close()
        finally:
            pool.fechar()

    def test_integracao_com_adaptador_falha_controlada(self):
        from app.tenant import commercial_observer_adapter as ad

        f = Fabrica()
        cfg = ConfiguracaoPool(tamanho=1, excesso_maximo=0, espera_conexao_s=0.05)
        pool = criar_pool_observacao(URL, cfg, engine_factory=f)
        ocupada = pool.session_factory()
        ocupada.execute(text("select 1"))
        try:
            fabrica = ad.criar_fabrica_sessao(pool.session_factory, 2.0)
            sessao = fabrica()
            with self.assertRaises(Exception):
                sessao.execute(text("select 1"), {})
            sessao.rollback()
            sessao.close()
        finally:
            ocupada.close()
            pool.fechar()


class IsolamentoTest(unittest.TestCase):
    def test_pools_independentes(self):
        f = Fabrica()
        a = criar_pool_observacao(URL, engine_factory=f)
        b = criar_pool_observacao(URL, engine_factory=f)
        a.session_factory().close()
        b.session_factory().close()
        self.assertIsNot(f.motores[0], f.motores[1])
        a.fechar()
        b.session_factory().close()

    def test_sessoes_nao_compartilhadas(self):
        pool = criar_pool_observacao(URL, engine_factory=Fabrica())
        s1, s2 = pool.session_factory(), pool.session_factory()
        self.assertIsNot(s1, s2)
        s1.close()
        s2.close()

    def test_engine_principal_preservado(self):
        principal = create_engine("sqlite://")
        antes = (principal.pool.__class__, principal.pool.status())
        pool = criar_pool_observacao(URL, engine_factory=Fabrica())
        pool.session_factory().close()
        pool.fechar()
        self.assertEqual((principal.pool.__class__, principal.pool.status()), antes)

    def test_conexao_devolvida_ao_pool_apos_rollback_e_close(self):
        f = Fabrica()
        pool = criar_pool_observacao(URL, engine_factory=f)
        s = pool.session_factory()
        s.execute(text("select 1"))
        self.assertEqual(f.motores[0].pool.checkedout(), 1)
        s.rollback()
        s.close()
        self.assertEqual(f.motores[0].pool.checkedout(), 0)


class SegurancaTest(unittest.TestCase):
    def test_repr_e_logs_sem_credenciais(self):
        pool = criar_pool_observacao(URL, engine_factory=Fabrica())
        pool.session_factory().close()
        for texto in (repr(pool), str(pool), repr(pool.configuracao)):
            self.assertNotIn(SEGREDO, texto)
            self.assertNotIn("host-inexistente", texto)
        with self.assertNoLogs(level="DEBUG"):
            pool.session_factory().close()

    def test_codigo_sem_ambiente_banco_principal_ou_escrita(self):
        src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        for proibido in ("os.environ", "getenv", "settings", "app.database", "fastapi",
                         "commit(", "INSERT", "UPDATE ", "DELETE ", "SessionLocal"):
            self.assertNotIn(proibido, src)
        imports = {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
        self.assertFalse({m for m in imports if m and m.startswith("app")})

    def test_nao_ha_url_derivada_de_empresa(self):
        src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("empresa", src.lower())


if __name__ == "__main__":
    unittest.main()
