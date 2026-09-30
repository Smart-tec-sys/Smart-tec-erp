import unittest

from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.fornecedor import FornecedorDB
from app.models.fornecedor_alias import FornecedorAliasDB
from app.models.funcao_tecnica_referencia import FuncaoTecnicaReferenciaDB
from app.models.produto import ProdutoDB
from app.schemas.fornecedor_alias import FornecedorAliasCreate
from app.services import fornecedor_alias_service as service
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


def _alias(original="Ação Distribuidora", fornecedor_id=2, **changes):
    values = {
        "fornecedor_id": fornecedor_id,
        "alias_original": original,
        "tipo": "NOME_COMERCIAL",
        "origem": "TABELA AÇÃO ATUAL 05.10.2020.pdf",
        "nivel_confianca": "FORTE",
        "status_revisao": "APROVADO",
    }
    values.update(changes)
    return FornecedorAliasCreate(**values)


class FornecedorAliasesFase7HTest(unittest.TestCase):
    def setUp(self):
        self.tenant1 = TenantContext(empresa_id=1)
        self.tenant2 = TenantContext(empresa_id=2)
        self.supplier1 = FornecedorDB(id=2, empresa_id=1, nome="A‡Æo Distribuidora", tipo="Fornecedor")
        self.supplier_other = FornecedorDB(id=20, empresa_id=2, nome="Fornecedor 2", tipo="Fornecedor")
        self.product = ProdutoDB(id=660, empresa_id=1, nome="Espaguete", valor_custo=1.44)
        self.equivalence = EmpresaEquivalenciaTecnicaDB(
            id=1, empresa_id=1, funcao_tecnica="ESPAGUETE_ROMANA_2_5MM",
            produto_id=660, fornecedor_id=None, prioridade=10, preferencial=True,
            ativo=True, configuracoes_locais={},
        )
        self.reference = FuncaoTecnicaReferenciaDB(
            id=1, empresa_id=1, fornecedor_id=None,
            funcao_tecnica="ESPAGUETE_ROMANA_2_5MM", nome_referencia="ESP 2,5",
            nome_normalizado="esp 2,5", nivel_confianca="FORTE",
            status_revisao="APROVADA", atributos_referencia={}, origem="PDF", ativo=True,
        )
        self.db = FakeSession({
            FornecedorDB: [self.supplier1, self.supplier_other],
            FornecedorAliasDB: [],
            ProdutoDB: [self.product],
            EmpresaEquivalenciaTecnicaDB: [self.equivalence],
            FuncaoTecnicaReferenciaDB: [self.reference],
        })

    def test_alias_pertence_a_fornecedor_da_mesma_empresa(self):
        row = service.create(self.db, self.tenant1, _alias())
        self.assertEqual((row.empresa_id, row.fornecedor_id), (1, 2))

    def test_fornecedor_de_outra_empresa_rejeitado(self):
        with self.assertRaises(PermissionError):
            service.create(self.db, self.tenant1, _alias(fornecedor_id=20))

    def test_aliases_iguais_podem_existir_em_empresas_diferentes(self):
        first = service.create(self.db, self.tenant1, _alias())
        second = service.create(self.db, self.tenant2, _alias(fornecedor_id=20))
        self.assertEqual(first.alias_normalizado, second.alias_normalizado)

    def test_conflito_ambiguo_na_mesma_empresa_e_bloqueado(self):
        service.create(self.db, self.tenant1, _alias())
        other = FornecedorDB(id=3, empresa_id=1, nome="Outro", tipo="Fornecedor")
        self.db.mapping[FornecedorDB].append(other)
        with self.assertRaisesRegex(ValueError, "ambíguo"):
            service.create(self.db, self.tenant1, _alias(fornecedor_id=3))

    def test_original_e_preservado_e_normalizacao_separada(self):
        original = "A‡Æo   Distribuidora"
        row = service.create(self.db, self.tenant1, _alias(original, tipo="NOME_HISTORICO"))
        self.assertEqual(row.alias_original, original)
        self.assertEqual(row.alias_normalizado, "ao distribuidora")

    def test_duas_variantes_reconhecem_fornecedor_2(self):
        service.create(self.db, self.tenant1, _alias("A‡Æo Distribuidora", tipo="NOME_HISTORICO"))
        service.create(self.db, self.tenant1, _alias("Ação Distribuidora"))
        for text in ("A‡Æo Distribuidora", "Ação Distribuidora"):
            result = service.recognize_supplier_candidates(self.db, self.tenant1, text)
            self.assertEqual([item["fornecedor_id"] for item in result], [2])

    def test_texto_sem_alias_nao_cria_nada(self):
        suppliers_before = list(self.db.mapping[FornecedorDB])
        result = service.recognize_supplier_candidates(self.db, self.tenant1, "Fineflex")
        self.assertEqual(result, [])
        self.assertEqual(self.db.mapping[FornecedorDB], suppliers_before)

    def test_reconhecimento_nao_altera_camadas_comerciais_ou_tecnicas(self):
        service.create(self.db, self.tenant1, _alias())
        product_before = (
            self.product.nome,
            self.product.valor_custo,
            getattr(self.product, "fornecedor_padrao_id", None),
        )
        equivalences_before = list(self.db.mapping[EmpresaEquivalenciaTecnicaDB])
        references_before = list(self.db.mapping[FuncaoTecnicaReferenciaDB])
        service.recognize_supplier_candidates(self.db, self.tenant1, "Ação Distribuidora")
        self.assertEqual(
            (
                self.product.nome,
                self.product.valor_custo,
                getattr(self.product, "fornecedor_padrao_id", None),
            ),
            product_before,
        )
        self.assertEqual(self.db.mapping[EmpresaEquivalenciaTecnicaDB], equivalences_before)
        self.assertEqual(self.db.mapping[FuncaoTecnicaReferenciaDB], references_before)

    def test_fineflex_e_arquivo_sem_origem_nao_sao_criados(self):
        service.create(self.db, self.tenant1, _alias())
        self.assertEqual(service.recognize_supplier_candidates(self.db, self.tenant1, "Fineflex"), [])
        self.assertEqual(service.recognize_supplier_candidates(self.db, self.tenant1, "128419.xlsx"), [])
        self.assertEqual(len(self.db.mapping[FornecedorDB]), 2)


if __name__ == "__main__":
    unittest.main()
