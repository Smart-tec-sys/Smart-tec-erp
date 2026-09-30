import unittest

from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.fornecedor import FornecedorDB
from app.models.funcao_tecnica_referencia import FuncaoTecnicaReferenciaDB
from app.models.produto import ProdutoDB
from app.schemas.funcao_tecnica_referencia import (
    FuncaoTecnicaReferenciaCreate,
    FuncaoTecnicaReferenciaUpdate,
)
from app.services import funcao_tecnica_referencia_service as service
from app.tenant.context import TenantContext


def _value(expression):
    return getattr(getattr(expression, "right", None), "value", None)


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *conditions):
        for condition in conditions:
            key = getattr(getattr(condition, "left", None), "key", None)
            value = _value(condition)
            if key:
                self.rows = [row for row in self.rows if getattr(row, key, None) == value]
        return self

    def order_by(self, *_):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, mapping):
        self.mapping = mapping
        self.next_id = 100

    def query(self, model):
        return FakeQuery(self.mapping.setdefault(model, []))

    def add(self, row):
        if row.id is None:
            row.id = self.next_id
            self.next_id += 1
        self.mapping.setdefault(type(row), []).append(row)

    def commit(self):
        pass

    def refresh(self, _):
        pass


def _data(**changes):
    values = {
        "funcao_tecnica": "ESPAGUETE_ROMANA_2_5MM",
        "nome_referencia": "ESP - ESPAGUETE / MACARRAO 2,50MM",
        "unidade_referencia": "RL",
        "nivel_confianca": "FORTE",
        "status_revisao": "APROVADA",
        "atributos_referencia": {
            "bitola_mm": 2.5,
            "embalagem": "ROLO",
            "comprimento_rolo_m": 200,
        },
        "origem": "TABELA AÇÃO ATUAL 05.10.2020.pdf",
        "origem_localizador": "página 32 / grupo 036 — ESPAGUETE",
        "origem_hash": "5cabbdf6ae93353845f2e5c6336658682fc57c1016cbc8235d599bd7656af8d8",
    }
    values.update(changes)
    return FuncaoTecnicaReferenciaCreate(**values)


class FuncaoTecnicaReferenciasFase7FTest(unittest.TestCase):
    def setUp(self):
        self.tenant1 = TenantContext(empresa_id=1)
        self.tenant2 = TenantContext(empresa_id=2)
        self.supplier1 = FornecedorDB(id=10, empresa_id=1, nome="Fornecedor 1", tipo="PJ")
        self.supplier2 = FornecedorDB(id=20, empresa_id=2, nome="Fornecedor 2", tipo="PJ")
        self.product660 = ProdutoDB(id=660, empresa_id=1, nome="Espaguete 2,5 mm", valor_custo=1.44)
        self.product661 = ProdutoDB(id=661, empresa_id=1, nome="Espaguete 3,0 mm", valor_custo=0.98)
        self.equivalence660 = EmpresaEquivalenciaTecnicaDB(
            id=1, empresa_id=1, funcao_tecnica="ESPAGUETE_ROMANA_2_5MM",
            produto_id=660, fornecedor_id=None, prioridade=10, preferencial=True,
            ativo=True, configuracoes_locais={},
        )
        self.db = FakeSession({
            FornecedorDB: [self.supplier1, self.supplier2],
            ProdutoDB: [self.product660, self.product661],
            EmpresaEquivalenciaTecnicaDB: [self.equivalence660],
            FuncaoTecnicaReferenciaDB: [],
        })

    def test_funcao_tecnica_inexistente_rejeitada(self):
        with self.assertRaises(ValueError):
            service.create(self.db, self.tenant1, _data(funcao_tecnica="INEXISTENTE"))

    def test_fornecedor_de_outra_empresa_rejeitado(self):
        with self.assertRaises(PermissionError):
            service.create(self.db, self.tenant1, _data(fornecedor_id=20))

    def test_referencia_sem_fornecedor_permitida(self):
        row = service.create(self.db, self.tenant1, _data())
        self.assertIsNone(row.fornecedor_id)
        self.assertEqual(row.empresa_id, 1)

    def test_duplicidade_contextual_rejeitada(self):
        service.create(self.db, self.tenant1, _data())
        with self.assertRaises(ValueError):
            service.create(self.db, self.tenant1, _data())

    def test_embalagens_diferentes_sao_referencias_distintas(self):
        first = service.create(self.db, self.tenant1, _data())
        second = service.create(self.db, self.tenant1, _data(
            atributos_referencia={
                "bitola_mm": 2.5,
                "embalagem": "ROLO",
                "comprimento_rolo_m": 485,
            }
        ))
        self.assertNotEqual(first.id, second.id)

    def test_empresas_diferentes_podem_usar_mesma_referencia(self):
        first = service.create(self.db, self.tenant1, _data())
        second = service.create(self.db, self.tenant2, _data())
        self.assertEqual(first.nome_normalizado, second.nome_normalizado)
        self.assertNotEqual(first.empresa_id, second.empresa_id)

    def test_referencia_nao_cria_equivalencia_comercial(self):
        before = list(self.db.mapping[EmpresaEquivalenciaTecnicaDB])
        service.create(self.db, self.tenant1, _data())
        self.assertEqual(self.db.mapping[EmpresaEquivalenciaTecnicaDB], before)

    def test_inativacao_nao_altera_produto_ou_equivalencia(self):
        row = service.create(self.db, self.tenant1, _data())
        product_before = (self.product660.nome, self.product660.valor_custo)
        equivalence_before = (
            self.equivalence660.produto_id,
            self.equivalence660.prioridade,
            self.equivalence660.preferencial,
            self.equivalence660.ativo,
        )

        updated = service.update(
            self.db, self.tenant1, row.id,
            FuncaoTecnicaReferenciaUpdate(ativo=False),
        )

        self.assertFalse(updated.ativo)
        self.assertEqual((self.product660.nome, self.product660.valor_custo), product_before)
        self.assertEqual(
            (
                self.equivalence660.produto_id,
                self.equivalence660.prioridade,
                self.equivalence660.preferencial,
                self.equivalence660.ativo,
            ),
            equivalence_before,
        )


if __name__ == "__main__":
    unittest.main()
