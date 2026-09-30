"""Testes do núcleo técnico universal criado na Fase 1."""

import dataclasses
import unittest
from pathlib import Path

from app.technical.catalog import (
    GRUPO_ACIONAMENTO_CORRENTE_ROMANA,
    GRUPO_COMANDO_ROMANA,
    TECHNICAL_CATALOG,
    VALID_TECHNICAL_FAMILIES,
    validate_technical_catalog,
)
from app.technical.functions import ROMANA_FUNCTION_CODES, ROLO_FUNCTION_CODES
from app.technical.models import TechnicalFunction, TechnicalRequirement
from app.technical.units import TechnicalUnit


class NucleoTecnicoFase1Test(unittest.TestCase):
    def test_catalogo_tem_codigos_unicos_familias_e_unidades_validas(self):
        validate_technical_catalog()
        self.assertEqual(len(TECHNICAL_CATALOG), len(set(TECHNICAL_CATALOG)))
        for function in TECHNICAL_CATALOG.values():
            self.assertIn(function.familia, VALID_TECHNICAL_FAMILIES)
            self.assertIsInstance(function.unidade_tecnica, TechnicalUnit)

    def test_funcoes_minimas_de_romana_e_rolo_estao_formalizadas(self):
        self.assertTrue(set(ROMANA_FUNCTION_CODES).issubset(TECHNICAL_CATALOG))
        self.assertTrue(set(ROLO_FUNCTION_CODES).issubset(TECHNICAL_CATALOG))

    def test_modelos_e_mapas_sao_imutaveis(self):
        function = TECHNICAL_CATALOG["ESPAGUETE_ROMANA_2_5MM"]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            function.codigo = "OUTRO"
        with self.assertRaises(TypeError):
            function.atributos_tecnicos["bitola_mm"] = 9

        requirement = TechnicalRequirement(
            funcao_tecnica=function.codigo,
            quantidade=8.295,
            unidade=TechnicalUnit.M,
            atributos={"bitola_mm": 2.5},
            origem_regra="CABECEIRA_E_VARETAS",
        )
        with self.assertRaises(TypeError):
            requirement.atributos["bitola_mm"] = 9

    def test_alternativas_de_romana_compartilham_grupo_exclusivo(self):
        command_codes = ("COMANDO_NORMAL_ROMANA", "COMANDO_REDUCAO_ROMANA")
        chain_codes = (
            "CORRENTE_SEM_FIM_ROMANA_BOLA10",
            "CORRENTE_JUTA_BOLA10_PERSONALIZADA",
        )
        self.assertEqual(
            {TECHNICAL_CATALOG[code].grupo_alternativa for code in command_codes},
            {GRUPO_COMANDO_ROMANA},
        )
        self.assertEqual(
            {TECHNICAL_CATALOG[code].grupo_alternativa for code in chain_codes},
            {GRUPO_ACIONAMENTO_CORRENTE_ROMANA},
        )

    def test_portabilidade_empresa_a_e_empresa_b(self):
        requirement = TechnicalRequirement(
            funcao_tecnica="ESPAGUETE_ROMANA_2_5MM",
            quantidade=8.295,
            unidade=TechnicalUnit.M,
            atributos={"bitola_mm": 2.5},
            origem_regra="CABECEIRA_E_VARETAS",
        )
        company_a_mapping = {requirement.funcao_tecnica: "item comercial A"}
        company_b_mapping = {requirement.funcao_tecnica: "item comercial B"}

        self.assertNotEqual(
            company_a_mapping[requirement.funcao_tecnica],
            company_b_mapping[requirement.funcao_tecnica],
        )
        self.assertEqual(requirement.quantidade, 8.295)
        self.assertEqual(requirement.unidade, TechnicalUnit.M)
        requirement_fields = {field.name for field in dataclasses.fields(requirement)}
        self.assertTrue({"produto", "fornecedor", "custo"}.isdisjoint(requirement_fields))

    def test_catalogo_nao_contem_campos_ou_referencias_comerciais(self):
        forbidden_fields = {
            "produto_id", "fornecedor_id", "sku", "codigo_comercial",
            "nome_comercial", "custo", "preco", "estoque", "fornecedor", "tenant",
        }
        function_fields = {field.name.casefold() for field in dataclasses.fields(TechnicalFunction)}
        requirement_fields = {field.name.casefold() for field in dataclasses.fields(TechnicalRequirement)}
        self.assertTrue(forbidden_fields.isdisjoint(function_fields | requirement_fields))

        technical_dir = Path(__file__).parents[1] / "app" / "technical"
        source = "\n".join(path.read_text(encoding="utf-8") for path in technical_dir.glob("*.py"))
        forbidden_commercial_ids = (660, 661, 272, 273, 667, 668)
        for commercial_id in forbidden_commercial_ids:
            self.assertNotIn(str(commercial_id), source)


if __name__ == "__main__":
    unittest.main()
