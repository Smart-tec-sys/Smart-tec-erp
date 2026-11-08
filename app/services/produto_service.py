import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.classificacao_tecnica_produto import ClassificacaoTecnicaProdutoDB
from app.models.produto import ProdutoDB
from app.models.opcao_auxiliar import OpcaoAuxiliarDB
from app.models.produto_historico import ProdutoHistoricoAlteracaoDB
from app.schemas.produto import ProdutoCreate, ProdutoUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant

logger = logging.getLogger(__name__)


_CLASSIFICACOES_TECNICAS = {
    "grupo_tecnico": 150,
    "familia_tecnica": 100,
    "modelo_tecnico": 100,
}


def get_all(db: Session, tenant: TenantContext, skip: int=0, limit: int=100):
    empresa_id = require_tenant(tenant)
    return (
        db.query(ProdutoDB)
        .filter(ProdutoDB.empresa_id == empresa_id)
        .order_by(ProdutoDB.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, produto_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    return db.query(ProdutoDB).filter(
        ProdutoDB.id == produto_id, ProdutoDB.empresa_id == empresa_id
    ).first()


def create(db: Session, data: ProdutoCreate, tenant: TenantContext):
    try:
        dados = data.dict()
        empresa_id = require_tenant(tenant)
        referencia_classificacoes = ProdutoDB(empresa_id=empresa_id)
        for campo in _CLASSIFICACOES_TECNICAS:
            if campo in dados:
                dados[campo] = _validar_classificacao(
                    db, referencia_classificacoes, campo, dados[campo],
                )
        novo_produto = ProdutoDB(**dados, empresa_id=empresa_id)

        # Calcula custo final básico
        novo_produto.custo_final = (
            float(novo_produto.valor_custo or 0)
            +float(novo_produto.despesas_acessorias or 0)
            +float(novo_produto.outras_despesas or 0)
        )

        db.add(novo_produto)
        db.commit()
        db.refresh(novo_produto)
        return novo_produto

    except Exception as e:
        db.rollback()
        print(f"Erro ao criar produto: {e}")
        raise e


def _opcoes_ativas(db: Session, empresa_id: int, categoria: str) -> set[str]:
    return {
        str(nome).strip()
        for (nome,) in db.query(OpcaoAuxiliarDB.nome).filter(
            OpcaoAuxiliarDB.empresa_id == empresa_id,
            OpcaoAuxiliarDB.categoria == categoria,
            func.lower(OpcaoAuxiliarDB.situacao) == "ativo",
        ).all()
        if nome and str(nome).strip()
    }


def _validar_classificacao(
    db: Session, produto: ProdutoDB, campo: str, valor: str | None,
) -> str | None:
    if valor is None:
        return None
    valor = " ".join(valor.split())
    if not valor:
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} não pode conter apenas espaços.")
    if valor == (getattr(produto, campo) or ""):
        return valor
    normalizado = valor.lower()
    classificacao = db.query(ClassificacaoTecnicaProdutoDB).filter(
        ClassificacaoTecnicaProdutoDB.empresa_id == produto.empresa_id,
        ClassificacaoTecnicaProdutoDB.tipo == campo,
        ClassificacaoTecnicaProdutoDB.nome_normalizado == normalizado,
    ).first()
    if classificacao is None:
        raise ValueError(
            f"{campo.replace('_', ' ').capitalize()} deve corresponder a uma classificação "
            "canônica da empresa."
        )
    return classificacao.nome


def get_technical_classifications(
    db: Session, tenant: TenantContext,
) -> dict[str, list[str]]:
    empresa_id = require_tenant(tenant)
    classificacoes = {
        campo: [] for campo in _CLASSIFICACOES_TECNICAS
    }
    for classificacao in db.query(ClassificacaoTecnicaProdutoDB).filter(
        ClassificacaoTecnicaProdutoDB.empresa_id == empresa_id,
    ).order_by(
        ClassificacaoTecnicaProdutoDB.tipo,
        ClassificacaoTecnicaProdutoDB.nome_normalizado,
    ).all():
        classificacoes[classificacao.tipo].append(classificacao.nome)
    return classificacoes


def _validar_unidade(
    db: Session, produto: ProdutoDB, campo: str, valor: str | None,
    opcoes_unidade_venda: set[str],
) -> None:
    if valor is None:
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} não pode ser removida.")
    valor = valor.strip()
    if not valor:
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} é obrigatória.")
    if valor == (getattr(produto, campo) or ""):
        return
    opcoes_existentes = {
        str(unidade).strip().casefold()
        for (unidade,) in db.query(getattr(ProdutoDB, campo)).filter(
            ProdutoDB.empresa_id == produto.empresa_id,
            getattr(ProdutoDB, campo).is_not(None),
        ).distinct().all()
        if unidade and str(unidade).strip()
    }
    if valor.casefold() not in opcoes_existentes | {
        item.casefold() for item in opcoes_unidade_venda
    }:
        raise ValueError(
            f"{campo.replace('_', ' ').capitalize()} deve corresponder a uma unidade "
            "ativa ou já utilizada no catálogo da empresa."
        )


def update(db: Session, produto_id: int, data: ProdutoUpdate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        produto = get_by_id(db, produto_id, tenant)

        if not produto:
            return None

        usuario_id = getattr(tenant, "user_id", None)
        try:
            usuario_id = int(usuario_id)
        except (TypeError, ValueError):
            usuario_id = None
        if usuario_id is None or usuario_id <= 0:
            raise PermissionError(
                "A edição exige uma identidade de usuário para registrar o histórico."
            )

        dados = data.model_dump(exclude_unset=True)
        opcoes_unidades = _opcoes_ativas(db, empresa_id, "unidade_venda")
        if "nome" in dados and (dados["nome"] is None or not dados["nome"].strip()):
            raise ValueError("Nome do produto é obrigatório.")

        for campo in _CLASSIFICACOES_TECNICAS:
            if campo in dados:
                valor = dados[campo]
                dados[campo] = _validar_classificacao(db, produto, campo, valor)

        for campo in ("grupo_produto",):
            if campo not in dados or dados[campo] is None:
                continue
            valor = dados[campo].strip()
            if not valor:
                raise ValueError("Grupo do produto não pode conter apenas espaços.")
            if valor != (produto.grupo_produto or "") and valor.casefold() not in {
                item.casefold() for item in _opcoes_ativas(db, empresa_id, campo)
            }:
                raise ValueError("Grupo do produto deve ser uma opção ativa da empresa.")
            dados[campo] = valor

        for campo in ("unidade_venda", "unidade", "unidade_compra", "unidade_controle"):
            if campo in dados:
                _validar_unidade(db, produto, campo, dados[campo], opcoes_unidades)
                dados[campo] = dados[campo].strip()

        for campo, valor in list(dados.items()):
            if isinstance(valor, str):
                valor = valor.strip()
                if not valor:
                    valor = None
                dados[campo] = valor

        for campo in (
            "valor_custo", "despesas_acessorias", "outras_despesas",
            "margem_lucro", "valor_venda",
        ):
            if campo in dados and dados[campo] is None:
                raise ValueError(f"{campo.replace('_', ' ').capitalize()} não pode ser removido.")

        campos_auditoria = tuple(dados)
        alteracoes = {}
        for campo, valor in dados.items():
            atual = getattr(produto, campo)
            if atual != valor:
                setattr(produto, campo, valor)
                alteracoes[campo] = {"antes": atual, "depois": valor}

        custo_final_anterior = float(produto.custo_final or 0)
        produto.custo_final = (
            float(produto.valor_custo or 0)
            + float(produto.despesas_acessorias or 0)
            + float(produto.outras_despesas or 0)
        )
        if custo_final_anterior != float(produto.custo_final):
            alteracoes["custo_final"] = {
                "antes": custo_final_anterior,
                "depois": float(produto.custo_final),
            }

        if alteracoes:
            db.add(ProdutoHistoricoAlteracaoDB(
                empresa_id=empresa_id,
                produto_id=produto.id,
                usuario_id=usuario_id,
                alteracoes=alteracoes,
            ))

        db.commit()
        db.refresh(produto)
        return produto

    except Exception as e:
        db.rollback()
        logger.exception("Falha ao atualizar produto %s na empresa %s", produto_id, empresa_id)
        raise e


def get_history(db: Session, produto_id: int, tenant: TenantContext):
    produto = get_by_id(db, produto_id, tenant)
    if produto is None:
        return None
    empresa_id = require_tenant(tenant)
    return db.query(ProdutoHistoricoAlteracaoDB).filter(
        ProdutoHistoricoAlteracaoDB.empresa_id == empresa_id,
        ProdutoHistoricoAlteracaoDB.produto_id == produto_id,
    ).order_by(
        ProdutoHistoricoAlteracaoDB.criado_em.desc(),
        ProdutoHistoricoAlteracaoDB.id.desc(),
    ).all()


def delete(db: Session, produto_id: int, tenant: TenantContext):
    try:
        produto = get_by_id(db, produto_id, tenant)

        if produto:
            historico = db.query(ProdutoHistoricoAlteracaoDB).filter(
                ProdutoHistoricoAlteracaoDB.empresa_id == require_tenant(tenant),
                ProdutoHistoricoAlteracaoDB.produto_id == produto_id,
            ).first()
            if historico is not None:
                raise ValueError(
                    "Produto possui histórico de alterações e não pode ser excluído fisicamente."
                )
            db.delete(produto)
            db.commit()
            return True

        return False

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError(
            "Produto possui vínculos históricos e não pode ser excluído fisicamente."
        ) from e
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar produto: {e}")
        return False
