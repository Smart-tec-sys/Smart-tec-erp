"""Alinhamento mínimo do ORM ao schema multiempresa já migrado no DEV."""

import dataclasses
import unittest

from app.models.cliente import ClienteDB
from app.models.fornecedor import FornecedorDB
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.models.produto import ProdutoDB
from app.technical.models import TechnicalFunction, TechnicalRequirement


class OrmTenantFase2CTest(unittest.TestCase):
    def test_modelos_legados_aceitam_empresa_nula(self):
        instances = (
            ProdutoDB(nome="Produto teste", empresa_id=None),
            FornecedorDB(nome="Fornecedor teste", tipo="PJ", empresa_id=None),
            ClienteDB(nome="Cliente teste", tipo="PF", empresa_id=None),
            OrcamentoDB(numero="TESTE", cliente_id=1, empresa_id=None),
        )
        for instance in instances:
            with self.subTest(model=type(instance).__name__):
                self.assertIsNone(instance.empresa_id)
                self.assertTrue(instance.__table__.c.empresa_id.nullable)

    def test_item_orcamento_nao_recebe_empresa_id(self):
        self.assertNotIn("empresa_id", OrcamentoItemDB.__table__.c)

    def test_nucleo_tecnico_permanece_global(self):
        forbidden = {"empresa_id", "tenant", "produto_id", "fornecedor_id", "custo"}
        function_fields = {field.name for field in dataclasses.fields(TechnicalFunction)}
        requirement_fields = {field.name for field in dataclasses.fields(TechnicalRequirement)}
        self.assertTrue(forbidden.isdisjoint(function_fields | requirement_fields))


if __name__ == "__main__":
    unittest.main()
