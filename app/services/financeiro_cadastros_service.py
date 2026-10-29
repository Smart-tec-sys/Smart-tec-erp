from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.financeiro_cadastros import (
    CentroCustoDB,
    ContaFinanceiraDB,
    FormaPagamentoDB,
    PlanoContaDB,
    SituacaoFinanceiraDB,
)


class CadastroNaoEncontrado(Exception):
    pass


class CadastroConflito(Exception):
    pass


# Campos que devem ser unicos por empresa (comparacao sem diferenciar caixa).
RECURSOS = {
    "contas-financeiras": (ContaFinanceiraDB, ("nome",)),
    "formas-pagamento": (FormaPagamentoDB, ("nome",)),
    "plano-contas": (PlanoContaDB, ("codigo", "nome")),
    "situacoes": (SituacaoFinanceiraDB, ("nome",)),
    "centros-custo": (CentroCustoDB, ("nome",)),
}

MENSAGEM_DUPLICADO = {
    "nome": "Já existe um cadastro com este nome.",
    "codigo": "Já existe um cadastro com este código.",
}


def _empresa_id(tenant) -> int:
    empresa_id = getattr(tenant, "empresa_id", None)
    if empresa_id is None:
        raise RuntimeError("Tenant atual sem empresa_id.")
    return int(empresa_id)


def listar(db: Session, recurso: str, tenant, apenas_ativos: bool = False):
    modelo, _ = RECURSOS[recurso]
    consulta = db.query(modelo).filter(modelo.empresa_id == _empresa_id(tenant))
    if apenas_ativos:
        consulta = consulta.filter(modelo.ativo.is_(True))
    ordem = modelo.codigo if recurso == "plano-contas" else modelo.nome
    return consulta.order_by(ordem, modelo.id).all()


def obter(db: Session, recurso: str, item_id: int, tenant, bloquear: bool = False):
    modelo, _ = RECURSOS[recurso]
    consulta = db.query(modelo).filter(
        modelo.id == item_id,
        modelo.empresa_id == _empresa_id(tenant),
    )
    if bloquear:
        consulta = consulta.with_for_update()
    item = consulta.first()
    if item is None:
        raise CadastroNaoEncontrado("Cadastro não encontrado.")
    return item


def _validar_unicidade(db, modelo, campos, empresa_id, valores, ignorar_id=None):
    for campo in campos:
        valor = valores.get(campo)
        if valor is None:
            continue
        consulta = db.query(modelo.id).filter(
            modelo.empresa_id == empresa_id,
            func.lower(getattr(modelo, campo)) == str(valor).lower(),
        )
        if ignorar_id is not None:
            consulta = consulta.filter(modelo.id != ignorar_id)
        if consulta.first() is not None:
            raise CadastroConflito(MENSAGEM_DUPLICADO[campo])


def _validar_pai(db, empresa_id, pai_id, item_id=None):
    if pai_id is None:
        return
    if item_id is not None and pai_id == item_id:
        raise CadastroConflito("Uma conta não pode ser pai dela mesma.")
    atual = (
        db.query(PlanoContaDB)
        .filter(PlanoContaDB.id == pai_id, PlanoContaDB.empresa_id == empresa_id)
        .first()
    )
    if atual is None:
        raise CadastroNaoEncontrado("Conta pai não encontrada.")
    # Impede ciclo: nenhum ancestral do pai pode ser o proprio item.
    visitados = set()
    while atual is not None and item_id is not None:
        if atual.id == item_id:
            raise CadastroConflito("A conta pai selecionada cria um ciclo na hierarquia.")
        if atual.id in visitados or atual.pai_id is None:
            break
        visitados.add(atual.id)
        atual = (
            db.query(PlanoContaDB)
            .filter(PlanoContaDB.id == atual.pai_id, PlanoContaDB.empresa_id == empresa_id)
            .first()
        )


def _regras_especificas(db, recurso, empresa_id, dados, item=None):
    """Validacoes por recurso. Retorna a situacao padrao a ser liberada, se houver."""
    if recurso == "formas-pagamento":
        conta_id = dados.get("conta_financeira_id")
        if conta_id is not None:
            conta = (
                db.query(ContaFinanceiraDB.id)
                .filter(
                    ContaFinanceiraDB.id == conta_id,
                    ContaFinanceiraDB.empresa_id == empresa_id,
                )
                .first()
            )
            if conta is None:
                raise CadastroNaoEncontrado("Conta financeira padrão não encontrada.")
        return None

    if recurso == "situacoes":
        def valor(campo, padrao=None):
            if campo in dados:
                return dados[campo]
            return getattr(item, campo) if item is not None else padrao

        if valor("padrao", False):
            if valor("quitado", False):
                raise CadastroConflito("Uma situação quitada não pode ser a situação padrão.")
            if not valor("ativo", True):
                raise CadastroConflito("A situação padrão precisa estar ativa.")
            return valor("tipo", "AMBOS")
    return None


def _liberar_padrao(db, empresa_id, tipo, ignorar_id=None):
    consulta = db.query(SituacaoFinanceiraDB).filter(
        SituacaoFinanceiraDB.empresa_id == empresa_id,
        SituacaoFinanceiraDB.tipo == tipo,
        SituacaoFinanceiraDB.padrao.is_(True),
    )
    if ignorar_id is not None:
        consulta = consulta.filter(SituacaoFinanceiraDB.id != ignorar_id)
    for outra in consulta.all():
        outra.padrao = False
    db.flush()

def criar(db: Session, recurso: str, tenant, dados: dict):
    modelo, unicos = RECURSOS[recurso]
    empresa_id = _empresa_id(tenant)
    _validar_unicidade(db, modelo, unicos, empresa_id, dados)
    if recurso == "plano-contas":
        _validar_pai(db, empresa_id, dados.get("pai_id"))
    tipo_padrao = _regras_especificas(db, recurso, empresa_id, dados)
    if tipo_padrao is not None:
        _liberar_padrao(db, empresa_id, tipo_padrao)
    item = modelo(empresa_id=empresa_id, **dados)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CadastroConflito("Já existe um cadastro com estes dados.")
    db.refresh(item)
    return item


def atualizar(db: Session, recurso: str, item_id: int, tenant, dados: dict):
    modelo, unicos = RECURSOS[recurso]
    empresa_id = _empresa_id(tenant)
    item = obter(db, recurso, item_id, tenant, bloquear=True)
    _validar_unicidade(db, modelo, unicos, empresa_id, dados, ignorar_id=item.id)
    if recurso == "plano-contas" and "pai_id" in dados:
        _validar_pai(db, empresa_id, dados["pai_id"], item.id)
    tipo_padrao = _regras_especificas(db, recurso, empresa_id, dados, item)
    if tipo_padrao is not None:
        _liberar_padrao(db, empresa_id, tipo_padrao, ignorar_id=item.id)
    for campo, valor in dados.items():
        setattr(item, campo, valor)
    item.atualizado_em = func.now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CadastroConflito("Já existe um cadastro com estes dados.")
    db.refresh(item)
    return item


def remover(db: Session, recurso: str, item_id: int, tenant):
    item = obter(db, recurso, item_id, tenant, bloquear=True)
    if recurso == "plano-contas":
        filho = (
            db.query(PlanoContaDB.id)
            .filter(
                PlanoContaDB.pai_id == item.id,
                PlanoContaDB.empresa_id == _empresa_id(tenant),
            )
            .first()
        )
        if filho is not None:
            raise CadastroConflito(
                "A conta possui subcontas. Remova ou reatribua as subcontas antes de excluir."
            )
    try:
        db.delete(item)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CadastroConflito("O cadastro está em uso e não pode ser excluído. Inative-o.")
