from sqlalchemy.orm import Session

from app.models.empresa import EmpresaDB
from app.tenant.onboarding import (
    TenantOnboardingInput,
    preview_zero_tenant,
)


def create_zero_tenant(
    db: Session,
    *,
    entrada: TenantOnboardingInput,
    nome_fantasia: str | None = None,
) -> EmpresaDB:
    """
    Cria uma empresa comercial completamente vazia.

    Não copia:
    - portfolio;
    - produtos;
    - fornecedores;
    - clientes;
    - orçamentos;
    - funcionários;
    - transportadoras;
    - opções auxiliares;
    - compras;
    - pedidos;
    - financeiro;
    - preços;
    - estoque;
    - custos.

    O núcleo técnico permanece global e não é persistido por tenant.

    A função controla sua própria transação:
    qualquer exceção provoca rollback integral.
    """

    preview = preview_zero_tenant(entrada)

    # Defesa adicional: o contrato da Fase 5 precisa continuar zerado.
    if preview.portfolio:
        raise RuntimeError("onboarding inválido: portfolio inicial não pode existir")

    if preview.produtos:
        raise RuntimeError("onboarding inválido: produtos iniciais não podem existir")

    if preview.fornecedores:
        raise RuntimeError("onboarding inválido: fornecedores iniciais não podem existir")

    if preview.clientes:
        raise RuntimeError("onboarding inválido: clientes iniciais não podem existir")

    if preview.orcamentos:
        raise RuntimeError("onboarding inválido: orçamentos iniciais não podem existir")

    if preview.estoque:
        raise RuntimeError("onboarding inválido: estoque inicial não pode existir")

    if preview.custos:
        raise RuntimeError("onboarding inválido: custos iniciais não podem existir")

    try:
        empresa = EmpresaDB(
            nome=entrada.nome.strip(),
            nome_fantasia=(
                nome_fantasia.strip()
                if nome_fantasia and nome_fantasia.strip()
                else None
            ),
            documento=(
                entrada.documento.strip()
                if entrada.documento and entrada.documento.strip()
                else None
            ),
            status="ATIVA",
            slug=entrada.slug.strip().lower(),
            configuracoes=dict(entrada.configuracoes_iniciais),
        )

        db.add(empresa)

        # Gera o ID e força validações/FKs/uniqueness do banco
        # antes do commit definitivo.
        db.flush()

        # Nenhum EmpresaPortfolioDB é criado aqui.
        # Nenhum dado comercial é clonado de outra empresa.

        db.commit()
        db.refresh(empresa)

        return empresa

    except Exception:
        db.rollback()
        raise