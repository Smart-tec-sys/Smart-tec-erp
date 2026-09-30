# Catálogo técnico versus catálogo comercial

## Núcleo global

`app/technical` define função, família, unidade técnica, grupos alternativos e
regras universais. Não conhece empresa, produto, fornecedor, custo ou estoque.

## Camada do tenant

Cada empresa possui produtos, fornecedores, unidades de compra/venda, custo,
estoque, disponibilidade, prioridade e equivalências próprios. Uma função pode
ter vários produtos candidatos; um único candidato ativo pode ser preferencial.

```text
função técnica global
        ↓
equivalência da empresa
        ↓
produto comercial ── fornecedor opcional
```

O identificador técnico é validado contra `TECHNICAL_CATALOG`. A persistência
não cria FK para código Python e não duplica fórmulas ou descrições universais.
