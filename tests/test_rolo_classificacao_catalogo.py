"""Regressoes de classificacao: atributos observados no catalogo DEV."""
import unittest
from types import SimpleNamespace
from app.services.rolo_simulacao import _tipo_rolo


class TestClassificacaoCatalogoRolo(unittest.TestCase):
    def produto(self, **campos):
        dados = dict(nome="ROL\u00d2 SCREEN 0,8%", grupo_produto="PERSIANAS",
                     unidade_venda="M\u00b2", tipo_produto=None, modelo_tecnico=None,
                     grupo_tecnico=None, familia_tecnica=None, modelo=None,
                     possui_composicao="N\u00e3o", movimenta_estoque="Sim")
        dados.update(campos)
        return SimpleNamespace(**dados)

    def test_comercial_3477_sem_modelo_tecnico(self):
        self.assertEqual(_tipo_rolo(self.produto()), "MANUAL")

    def test_linhas_comerciais(self):
        for nome in ("ROLO SCREEN 1%", "ROLO SCREEN 3%", "ROLO SCREEN 5%",
                     "ROLO BLACKOUT NAPOLES", "ROLO BK.NAPOLES", "ROLO TRANSLUCIDA"):
            with self.subTest(nome=nome):
                self.assertEqual(_tipo_rolo(self.produto(nome=nome)), "MANUAL")

    def test_motorizado_exige_produto_final(self):
        self.assertEqual(_tipo_rolo(self.produto(nome="ROLO SCREEN 3% MOTORIZADA")), "MOTORIZADA")
        self.assertIsNone(_tipo_rolo(self.produto(
            nome="ROLO BK NAPOLES MOTORIZADA", modelo_tecnico="ROLO",
            modelo="MOTORIZADA", tipo_produto="Componente",
            grupo_produto="Componentes", grupo_tecnico="MOTORES",
            possui_composicao="Sim")))

    def test_componentes_prevalecem_sobre_modelo_rolo(self):
        for nome in ("COMANDO ROLO 32MM", "TUBO P/ ROLO 41MM",
                     "BASE CHATA 2 P/ ROLO", "TECIDO ROLO SCREEN",
                     "ROLO SCREEN COMANDO", "ROLO SCREEN SUPORTE",
                     "CORRENTE ROLO", "PONTEIRA ROLO", "TAMPA ROLO"):
            with self.subTest(nome=nome):
                self.assertIsNone(_tipo_rolo(self.produto(nome=nome, modelo_tecnico="ROLO")))

    def test_metadados_de_componentes_prevalecem(self):
        for campo, valor in (("tipo_produto", "Componente"), ("grupo_produto", "Tecidos"),
                             ("grupo_tecnico", "PERFIS_PERSIANAS_ROLO"),
                             ("familia_tecnica", "FAM_TECIDO_JP_SCREEN_3_ROLO_50M"),
                             ("grupo_tecnico", "TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL")):
            with self.subTest(campo=campo):
                self.assertIsNone(_tipo_rolo(self.produto(modelo_tecnico="ROLO", **{campo: valor})))

    def test_nome_isolado_e_campos_conflitantes_nao_bastam(self):
        for campos in (dict(grupo_produto=None), dict(unidade_venda="ML"),
                       dict(modelo_tecnico="ROMANA"), dict(modelo="DOUBLE VISION"),
                       dict(familia_tecnica="ROMANA"), dict(nome="CONTROLE ROLO"),
                       dict(nome="ROLO DESCONHECIDO")):
            with self.subTest(campos=campos):
                self.assertIsNone(_tipo_rolo(self.produto(**campos)))


if __name__ == "__main__":
    unittest.main()
