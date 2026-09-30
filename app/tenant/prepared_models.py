"""Plano da segunda etapa; não modifica os modelos ORM legados ativos."""

from types import MappingProxyType


TENANT_COLUMN_PLAN = MappingProxyType({
    "produtos": MappingProxyType({"nullable": True}),
    "fornecedores": MappingProxyType({"nullable": True}),
    "clientes": MappingProxyType({"nullable": True}),
    "orcamentos": MappingProxyType({"nullable": True}),
})

# A ativação destas colunas no ORM só ocorrerá depois da migration no DEV.
DEFERRED_TENANT_UNIQUENESS = (
    ("produtos", "empresa_id", "codigo_interno"),
    ("fornecedores", "empresa_id", "documento"),
)
