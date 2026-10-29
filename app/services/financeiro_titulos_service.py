from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import bindparam, case, func, text
from sqlalchemy.orm import Session

from app.models.financeiro_cadastros import (
    CentroCustoDB,
    ContaFinanceiraDB,
    FormaPagamentoDB,
    PlanoContaDB,
    SituacaoFinanceiraDB,
)
from app.models.financeiro import FinanceiroBaixaDB as B
from app.models.financeiro import FinanceiroDB as T


class TituloNaoEncontrado(Exception):
    pass


class TituloInvalido(Exception):
    """Dado inconsistente (-> 422/400)."""


class TituloConflito(Exception):
    """Operacao bloqueada por vinculo ou estado do titulo (-> 409)."""


_CENT = Decimal("0.01")
LIMITE_VALOR_COLUNA = Decimal("9999999999.99")  # financeiro.valor e NUMERIC(12,2)
_DISPONIVEL = {"R": ("RECEBER", "AMBOS"), "P": ("PAGAR", "AMBOS")}
_SITUACAO = {"R": ("RECEBER", "AMBOS"), "P": ("PAGAR", "AMBOS")}
_PLANO = {"R": "RECEITA", "P": "DESPESA"}
_CAMPOS_VALOR = {"valor_original", "desconto", "juros"}
# Campos que nao podem mudar em titulo vinculado a Venda/RT/Contabilidade ou baixado.
_CAMPOS_PROTEGIDOS = _CAMPOS_VALOR | {"cliente_id", "fornecedor_id"}


def _empresa_id(tenant) -> int:
    empresa_id = getattr(tenant, "empresa_id", None)
    if empresa_id is None:
        raise RuntimeError("Tenant atual sem empresa_id.")
    return int(empresa_id)


def _quitado(t: T) -> bool:
    return (t.status or "").upper() == "PAGO" or (t.valor_pago or 0) > 0


def _possui_baixas(db: Session, t: T) -> bool:
    return db.execute(text("SELECT 1 FROM financeiro_baixas WHERE financeiro_id = :id LIMIT 1"), {"id": t.id}).first() is not None


def _vinculado(db: Session, t: T) -> bool:
    if t.pedido_id is not None:
        return True
    for tabela in ("representantes_rt", "contabilidade_obrigacoes"):
        achou = db.execute(
            text(f"SELECT 1 FROM {tabela} WHERE financeiro_id = :id LIMIT 1"),
            {"id": t.id},
        ).first()
        if achou:
            return True
    return False


def _origem(t: T, rt_ids, contab_ids) -> str:
    if t.id in contab_ids:
        return "CONTABILIDADE"
    if t.id in rt_ids:
        return "RT"
    if t.pedido_id is not None:
        return "VENDA" if t.tipo == "R" else "RT"
    return "MANUAL"


def calcular_valores(valor, status, cash, credito, n_ativas):
    """Regra UNICA de saldo (usada por listagem, indicadores, baixa e estorno).

    valor  = valor liquido previsto do titulo (valor_original - desconto + juros do titulo).
    Cada baixa ativa quita (valor - juros_baixa + desconto_baixa) do titulo e movimenta
    `valor` em dinheiro. Logo:
        valor_pago = soma(valor das baixas ativas)            (dinheiro efetivo)
        saldo      = max(valor_titulo - soma(valor - juros + desconto), 0)
    Titulo historico PAGO sem baixas (baixado pelos fluxos legados): valor_pago = valor, saldo = 0.
    """
    valor = valor or Decimal("0")
    if n_ativas:
        return (cash or Decimal("0")), max(valor - (credito or Decimal("0")), Decimal("0"))
    if (status or "").upper() == "PAGO":
        return valor, Decimal("0")
    return Decimal("0"), valor


def _agregado_baixas(db: Session, ids, empresa_id: int) -> dict:
    if not ids:
        return {}
    ativo = B.estornada_em.is_(None)
    linhas = (
        db.query(
            B.financeiro_id,
            func.sum(case((ativo, B.valor), else_=0)),
            func.sum(case((ativo, B.valor - B.juros + B.desconto), else_=0)),
            func.sum(case((ativo, 1), else_=0)),
            func.count(B.id),
        )
        .filter(B.empresa_id == empresa_id, B.financeiro_id.in_(list(ids)))
        .group_by(B.financeiro_id)
        .all()
    )
    return {
        i: (Decimal(str(c or 0)), Decimal(str(cr or 0)), int(na or 0), int(nt or 0))
        for i, c, cr, na, nt in linhas
    }


def _nomes(db: Session, tabela: str, ids, empresa_id: int, coluna: str = "nome") -> dict:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    consulta = text(f"SELECT id, {coluna} FROM {tabela} WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    return {r[0]: r[1] for r in db.execute(consulta, {"ids": list(ids)})}


def _ids_vinculo(db: Session, tabela: str, ids) -> set:
    if not ids:
        return set()
    consulta = text(f"SELECT financeiro_id FROM {tabela} WHERE financeiro_id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    return {r[0] for r in db.execute(consulta, {"ids": list(ids)})}


def _saidas(db: Session, itens, empresa_id: int) -> list:
    ids = [t.id for t in itens]
    agg = _agregado_baixas(db, ids, empresa_id)
    rt_ids = _ids_vinculo(db, "representantes_rt", ids)
    contab_ids = _ids_vinculo(db, "contabilidade_obrigacoes", ids)
    clientes = _nomes(db, "clientes", [t.cliente_id for t in itens], empresa_id)
    fornecedores = _nomes(db, "fornecedores", [t.fornecedor_id for t in itens], empresa_id)
    pedidos = _nomes(db, "pedidos", [t.pedido_id for t in itens], empresa_id, "numero")
    saidas = []
    for t in itens:
        cash, credito, n_ativas, n_total = agg.get(t.id, (Decimal("0"), Decimal("0"), 0, 0))
        valor_pago, saldo = calcular_valores(t.valor, t.status, cash, credito, n_ativas)
        origem = _origem(t, rt_ids, contab_ids)
        vinculado = origem != "MANUAL"
        quitado = (t.status or "").upper() == "PAGO" or valor_pago > 0
        dados = {c.name: getattr(t, c.name) for c in T.__table__.columns}
        dados.update(
            valor_original=t.valor_original if t.valor_original is not None else t.valor,
            desconto=t.desconto or Decimal("0"),
            juros=t.juros or Decimal("0"),
            valor_pago=valor_pago,
            saldo=saldo,
            recorrente=bool(t.recorrente),
            vinculado=vinculado,
            origem=origem,
            cliente_nome=clientes.get(t.cliente_id),
            fornecedor_nome=fornecedores.get(t.fornecedor_id),
            pedido_numero=pedidos.get(t.pedido_id),
            qtd_baixas=n_ativas,
            qtd_baixas_total=n_total,
            pode_excluir=not vinculado and not quitado and n_total == 0,
            pode_baixar=(origem in ("MANUAL", "VENDA")) and (t.status or "").upper() == "ABERTO" and saldo > 0,
        )
        saidas.append(dados)
    return saidas


def _saida(db: Session, t: T) -> dict:
    return _saidas(db, [t], t.empresa_id)[0]

def _validar_pessoa(db, tabela, pessoa_id, empresa_id, rotulo):
    achou = db.execute(
        text(f"SELECT 1 FROM {tabela} WHERE id = :id AND empresa_id = :e"),
        {"id": pessoa_id, "e": empresa_id},
    ).first()
    if not achou:
        raise TituloInvalido(f"{rotulo} nao encontrado nesta empresa.")


def _buscar(db, modelo, item_id, empresa_id, rotulo):
    obj = (
        db.query(modelo)
        .filter(modelo.id == item_id, modelo.empresa_id == empresa_id)
        .first()
    )
    if obj is None:
        raise TituloInvalido(f"{rotulo} nao encontrado nesta empresa.")
    return obj


def _validar_referencias(db, empresa_id: int, tipo: str, dados: dict, anterior: Optional[T] = None):
    """Todo vinculo precisa ser da mesma empresa, ativo (se alterado) e compativel com R/P."""

    def mudou(campo):
        return anterior is None or getattr(anterior, campo) != dados.get(campo)

    if dados.get("cliente_id") is not None:
        if tipo == "P":
            raise TituloInvalido("Conta a pagar nao aceita cliente.")
        if mudou("cliente_id"):
            _validar_pessoa(db, "clientes", dados["cliente_id"], empresa_id, "Cliente")
    if dados.get("fornecedor_id") is not None:
        if tipo == "R":
            raise TituloInvalido("Conta a receber nao aceita fornecedor.")
        if mudou("fornecedor_id"):
            _validar_pessoa(db, "fornecedores", dados["fornecedor_id"], empresa_id, "Fornecedor")

    if dados.get("conta_financeira_id") is not None and mudou("conta_financeira_id"):
        conta = _buscar(db, ContaFinanceiraDB, dados["conta_financeira_id"], empresa_id, "Conta financeira")
        if not conta.ativo:
            raise TituloInvalido("Conta financeira inativa.")
    if dados.get("forma_pagamento_id") is not None and mudou("forma_pagamento_id"):
        forma = _buscar(db, FormaPagamentoDB, dados["forma_pagamento_id"], empresa_id, "Forma de pagamento")
        if not forma.ativo:
            raise TituloInvalido("Forma de pagamento inativa.")
        if forma.disponivel_para not in _DISPONIVEL[tipo]:
            raise TituloInvalido("Forma de pagamento nao disponivel para este tipo de titulo.")
    if dados.get("plano_conta_id") is not None and mudou("plano_conta_id"):
        plano = _buscar(db, PlanoContaDB, dados["plano_conta_id"], empresa_id, "Plano de contas")
        if not plano.ativo:
            raise TituloInvalido("Plano de contas inativo.")
        if plano.tipo != _PLANO[tipo]:
            raise TituloInvalido("Plano de contas incompativel com o tipo do titulo.")
    if dados.get("centro_custo_id") is not None and mudou("centro_custo_id"):
        centro = _buscar(db, CentroCustoDB, dados["centro_custo_id"], empresa_id, "Centro de custo")
        if not centro.ativo:
            raise TituloInvalido("Centro de custo inativo.")
    if dados.get("situacao_financeira_id") is not None and mudou("situacao_financeira_id"):
        situacao = _buscar(db, SituacaoFinanceiraDB, dados["situacao_financeira_id"], empresa_id, "Situacao")
        if not situacao.ativo:
            raise TituloInvalido("Situacao inativa.")
        if situacao.tipo not in _SITUACAO[tipo]:
            raise TituloInvalido("Situacao incompativel com o tipo do titulo.")
        if situacao.quitado:
            raise TituloInvalido("Situacao quitada so pode ser aplicada pela baixa (ainda nao disponivel).")


def _calcular_valor(original: Decimal, desconto: Decimal, juros: Decimal) -> Decimal:
    valor = (original - desconto + juros).quantize(_CENT)
    if valor <= 0:
        raise TituloInvalido("O valor liquido do titulo deve ser maior que zero.")
    if valor > LIMITE_VALOR_COLUNA:
        raise TituloInvalido("Valor liquido acima do limite permitido.")
    return valor


def _filtrar(consulta, empresa_id, f: dict, hoje):
    consulta = consulta.filter(T.empresa_id == empresa_id)
    if f.get("tipo"):
        consulta = consulta.filter(T.tipo == f["tipo"].strip().upper())
    if f.get("status"):
        consulta = consulta.filter(T.status == f["status"].strip().upper())
    if f.get("vencimento_inicial"):
        consulta = consulta.filter(T.vencimento >= f["vencimento_inicial"])
    if f.get("vencimento_final"):
        consulta = consulta.filter(T.vencimento <= f["vencimento_final"])
    for campo in (
        "cliente_id", "fornecedor_id", "pedido_id", "conta_financeira_id",
        "forma_pagamento_id", "plano_conta_id", "centro_custo_id", "situacao_financeira_id",
    ):
        if f.get(campo) is not None:
            consulta = consulta.filter(getattr(T, campo) == f[campo])
    if f.get("categoria") and f["categoria"].strip():
        consulta = consulta.filter(T.categoria.ilike(f["categoria"].strip()))
    if f.get("q") and f["q"].strip():
        consulta = consulta.filter(T.descricao.ilike(f"%{f['q'].strip()}%"))
    venc = (f.get("vencimento_status") or "").strip().upper()
    if venc:
        consulta = consulta.filter(T.status == "ABERTO")
        if venc == "VENCIDO":
            consulta = consulta.filter(T.vencimento < hoje)
        elif venc == "HOJE":
            consulta = consulta.filter(T.vencimento == hoje)
        elif venc == "A_VENCER":
            consulta = consulta.filter(T.vencimento > hoje)
        else:
            raise TituloInvalido("vencimento_status invalido.")
    return consulta


def listar(db: Session, tenant, *, limit: int = 100, offset: int = 0, hoje=None, **filtros):
    empresa_id = _empresa_id(tenant)
    consulta = _filtrar(db.query(T), empresa_id, filtros, hoje or date.today())
    itens = (
        consulta.order_by(T.vencimento, T.id)
        .limit(max(1, min(limit, 500)))
        .offset(max(0, offset))
        .all()
    )
    return _saidas(db, itens, empresa_id)


def indicadores(db: Session, tenant, *, hoje=None, **filtros) -> dict:
    """Totais reais do periodo/filtros. `status` e `vencimento_status` nao se aplicam aos cartoes."""
    empresa_id = _empresa_id(tenant)
    hoje = hoje or date.today()
    filtros = {k: v for k, v in filtros.items() if k not in ("status", "vencimento_status")}
    linhas = _filtrar(db.query(T.id, T.valor, T.status, T.vencimento), empresa_id, filtros, hoje).all()
    agg = _agregado_baixas(db, [l[0] for l in linhas], empresa_id)
    cartoes = {k: {"quantidade": 0, "total": Decimal("0")} for k in ("total_periodo", "vencidos", "vencem_hoje", "a_vencer", "quitados")}

    def somar(chave, valor):
        cartoes[chave]["quantidade"] += 1
        cartoes[chave]["total"] += valor

    for tid, valor, status, vencimento in linhas:
        status = (status or "").upper()
        if status == "CANCELADO":
            continue
        cash, credito, n_ativas, _ = agg.get(tid, (Decimal("0"), Decimal("0"), 0, 0))
        valor_pago, saldo = calcular_valores(valor, status, cash, credito, n_ativas)
        somar("total_periodo", valor)
        if status == "PAGO":
            somar("quitados", valor_pago)
        elif status == "ABERTO":
            if vencimento < hoje:
                somar("vencidos", saldo)
            elif vencimento == hoje:
                somar("vencem_hoje", saldo)
            else:
                somar("a_vencer", saldo)
    return cartoes

def _obter_modelo(db: Session, titulo_id: int, tenant, bloquear: bool = False) -> T:
    consulta = db.query(T).filter(T.id == titulo_id, T.empresa_id == _empresa_id(tenant))
    if bloquear:
        consulta = consulta.with_for_update()
    t = consulta.first()
    if t is None:
        raise TituloNaoEncontrado("Titulo nao encontrado.")
    return t


def obter(db: Session, titulo_id: int, tenant) -> dict:
    return _saida(db, _obter_modelo(db, titulo_id, tenant))


def criar(db: Session, tenant, dados: dict) -> dict:
    empresa_id = _empresa_id(tenant)
    tipo = dados["tipo"]
    _validar_referencias(db, empresa_id, tipo, dados)
    valor = _calcular_valor(dados["valor_original"], dados.get("desconto") or Decimal("0"), dados.get("juros") or Decimal("0"))
    t = T(
        empresa_id=empresa_id,
        tipo=tipo,
        descricao=dados["descricao"],
        competencia=dados.get("competencia"),
        valor_original=dados["valor_original"],
        desconto=dados.get("desconto") or Decimal("0"),
        juros=dados.get("juros") or Decimal("0"),
        valor=valor,
        vencimento=dados["vencimento"],
        status="ABERTO",
        valor_pago=Decimal("0"),
        recorrente=False,
        **{
            k: dados.get(k)
            for k in (
                "cliente_id",
                "fornecedor_id",
                "conta_financeira_id",
                "forma_pagamento_id",
                "plano_conta_id",
                "centro_custo_id",
                "situacao_financeira_id",
                "categoria",
                "observacao",
            )
        },
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _saida(db, t)


def atualizar(db: Session, titulo_id: int, tenant, dados: dict) -> dict:
    empresa_id = _empresa_id(tenant)
    t = _obter_modelo(db, titulo_id, tenant, bloquear=True)
    for campo in ("descricao", "vencimento"):
        if campo in dados and dados[campo] is None:
            raise TituloInvalido("Campo obrigatorio nao pode ser removido.")
    for campo in _CAMPOS_VALOR:
        if campo in dados and dados[campo] is None:
            dados.pop(campo)

    trava = _quitado(t) or _vinculado(db, t)
    mudancas_protegidas = [
        c for c in _CAMPOS_PROTEGIDOS if c in dados and dados[c] != getattr(t, c)
    ]
    if trava and mudancas_protegidas:
        raise TituloConflito(
            "Titulo vinculado a Venda/RT/Contabilidade ou ja baixado: valores e pessoa nao podem ser alterados."
        )

    efetivo = {c: dados.get(c, getattr(t, c)) for c in (
        "cliente_id", "fornecedor_id", "conta_financeira_id", "forma_pagamento_id",
        "plano_conta_id", "centro_custo_id", "situacao_financeira_id")}
    _validar_referencias(db, empresa_id, t.tipo, efetivo, anterior=t)

    if _CAMPOS_VALOR & dados.keys():
        original = dados.get("valor_original")
        if original is None:
            original = t.valor_original if t.valor_original is not None else t.valor
        desconto = dados.get("desconto", t.desconto or Decimal("0"))
        juros = dados.get("juros", t.juros or Decimal("0"))
        t.valor = _calcular_valor(original, desconto, juros)
        t.valor_original = original
        t.desconto = desconto
        t.juros = juros

    for campo in (
        "descricao", "competencia", "vencimento", "cliente_id", "fornecedor_id",
        "conta_financeira_id", "forma_pagamento_id", "plano_conta_id",
        "centro_custo_id", "situacao_financeira_id", "categoria", "observacao",
    ):
        if campo in dados:
            setattr(t, campo, dados[campo])
    db.commit()
    db.refresh(t)
    return _saida(db, t)


def remover(db: Session, titulo_id: int, tenant) -> None:
    t = _obter_modelo(db, titulo_id, tenant, bloquear=True)
    if _vinculado(db, t):
        raise TituloConflito("Titulo vinculado a Venda, RT ou Contabilidade nao pode ser excluido.")
    if _quitado(t) or _possui_baixas(db, t):
        raise TituloConflito("Titulo baixado nao pode ser excluido.")
    db.delete(t)
    db.commit()

# ---------------------------------------------------------------- baixas
def _baixa_saida(b: B) -> dict:
    dados = {c.name: getattr(b, c.name) for c in B.__table__.columns}
    dados["ativa"] = b.estornada_em is None
    return dados


def _situacao_quitada(db: Session, empresa_id: int, tipo: str):
    base = db.query(SituacaoFinanceiraDB).filter(
        SituacaoFinanceiraDB.empresa_id == empresa_id,
        SituacaoFinanceiraDB.ativo.is_(True),
        SituacaoFinanceiraDB.quitado.is_(True),
        SituacaoFinanceiraDB.tipo.in_(_SITUACAO[tipo]),
    )
    return (
        base.order_by(SituacaoFinanceiraDB.nome.ilike("pago").desc(), SituacaoFinanceiraDB.id).first()
    )


def _situacao_padrao(db: Session, empresa_id: int, tipo: str):
    return (
        db.query(SituacaoFinanceiraDB)
        .filter(
            SituacaoFinanceiraDB.empresa_id == empresa_id,
            SituacaoFinanceiraDB.ativo.is_(True),
            SituacaoFinanceiraDB.padrao.is_(True),
            SituacaoFinanceiraDB.quitado.is_(False),
            SituacaoFinanceiraDB.tipo.in_(_SITUACAO[tipo]),
        )
        .order_by(SituacaoFinanceiraDB.id)
        .first()
    )


def _recalcular(db: Session, t: T) -> None:
    """Unico ponto que atualiza os resumos do titulo a partir das baixas ativas."""
    agg = _agregado_baixas(db, [t.id], t.empresa_id).get(t.id, (Decimal("0"), Decimal("0"), 0, 0))
    cash, credito, n_ativas, _ = agg
    ultima = (
        db.query(func.max(B.data_baixa))
        .filter(B.financeiro_id == t.id, B.empresa_id == t.empresa_id, B.estornada_em.is_(None))
        .scalar()
    )
    _, saldo = calcular_valores(t.valor, "ABERTO", cash, credito, n_ativas)
    t.valor_pago = cash
    t.data_baixa = ultima
    atual = db.get(SituacaoFinanceiraDB, t.situacao_financeira_id) if t.situacao_financeira_id else None
    if saldo <= 0 and n_ativas:
        t.status = "PAGO"
        t.pagamento = ultima
        quitada = _situacao_quitada(db, t.empresa_id, t.tipo)
        if quitada is not None:
            t.situacao_financeira_id = quitada.id
    else:
        t.status = "ABERTO"
        t.pagamento = None
        if atual is not None and atual.quitado:
            padrao = _situacao_padrao(db, t.empresa_id, t.tipo)
            t.situacao_financeira_id = padrao.id if padrao is not None else None


def baixar(db: Session, titulo_id: int, tenant, dados: dict) -> dict:
    empresa_id = _empresa_id(tenant)
    t = _obter_modelo(db, titulo_id, tenant, bloquear=True)
    tipo = t.tipo
    if (t.status or "").upper() == "CANCELADO":
        raise TituloConflito("Titulo cancelado nao pode receber baixa.")
    rt_ids = _ids_vinculo(db, "representantes_rt", [t.id])
    contab_ids = _ids_vinculo(db, "contabilidade_obrigacoes", [t.id])
    if _origem(t, rt_ids, contab_ids) in ("RT", "CONTABILIDADE"):
        raise TituloConflito(
            "Titulo de RT/Contabilidade deve ser baixado pelo proprio modulo de origem."
        )

    valor = dados["valor"]
    juros = dados.get("juros") or Decimal("0")
    desconto = dados.get("desconto") or Decimal("0")
    if valor <= 0:
        raise TituloInvalido("O valor da baixa deve ser maior que zero.")
    if juros < 0 or desconto < 0:
        raise TituloInvalido("Juros e desconto da baixa nao podem ser negativos.")
    quitacao = (valor - juros + desconto).quantize(_CENT)
    if quitacao <= 0:
        raise TituloInvalido("Juros da baixa nao podem consumir todo o valor pago.")

    agg = _agregado_baixas(db, [t.id], empresa_id).get(t.id, (Decimal("0"), Decimal("0"), 0, 0))
    _, saldo = calcular_valores(t.valor, t.status, *agg[:3])
    if saldo <= 0:
        raise TituloConflito("Titulo ja esta quitado.")
    if quitacao > saldo:
        raise TituloInvalido(f"A baixa quita {quitacao} e excede o saldo do titulo ({saldo}).")

    forma = conta = None
    if dados.get("forma_pagamento_id") is not None:
        forma = _buscar(db, FormaPagamentoDB, dados["forma_pagamento_id"], empresa_id, "Forma de pagamento")
        if not forma.ativo:
            raise TituloInvalido("Forma de pagamento inativa.")
        if forma.disponivel_para not in _DISPONIVEL[tipo]:
            raise TituloInvalido("Forma de pagamento nao disponivel para este tipo de titulo.")
    conta_id = dados.get("conta_financeira_id")
    if conta_id is not None:
        conta = _buscar(db, ContaFinanceiraDB, conta_id, empresa_id, "Conta financeira")
        if not conta.ativo:
            raise TituloInvalido("Conta financeira inativa.")
    # Sem conta informada: conta padrao da forma e, depois, a conta do titulo.
    if conta is None:
        conta_id = (forma.conta_financeira_id if forma is not None else None) or t.conta_financeira_id

    baixa = B(
        empresa_id=empresa_id,
        financeiro_id=t.id,
        data_baixa=dados["data_baixa"],
        valor=valor,
        juros=juros,
        desconto=desconto,
        conta_financeira_id=conta_id,
        forma_pagamento_id=forma.id if forma is not None else t.forma_pagamento_id,
        observacao=_texto_ou_none(dados.get("observacao")),
    )
    db.add(baixa)
    db.flush()
    _recalcular(db, t)
    db.commit()
    db.refresh(baixa)
    db.refresh(t)
    return {"baixa": _baixa_saida(baixa), "titulo": _saida(db, t)}


def estornar(db: Session, baixa_id: int, tenant) -> dict:
    empresa_id = _empresa_id(tenant)
    baixa = db.query(B).filter(B.id == baixa_id, B.empresa_id == empresa_id).first()
    if baixa is None:
        raise TituloNaoEncontrado("Baixa nao encontrada.")
    t = _obter_modelo(db, baixa.financeiro_id, tenant, bloquear=True)
    db.refresh(baixa)
    if baixa.estornada_em is not None:
        raise TituloConflito("Esta baixa ja foi estornada.")
    baixa.estornada_em = datetime.now()
    db.flush()
    _recalcular(db, t)
    db.commit()
    db.refresh(baixa)
    db.refresh(t)
    return {"baixa": _baixa_saida(baixa), "titulo": _saida(db, t)}


def listar_baixas(db: Session, titulo_id: int, tenant) -> list:
    empresa_id = _empresa_id(tenant)
    _obter_modelo(db, titulo_id, tenant)
    itens = (
        db.query(B)
        .filter(B.financeiro_id == titulo_id, B.empresa_id == empresa_id)
        .order_by(B.data_baixa, B.id)
        .all()
    )
    return [_baixa_saida(b) for b in itens]


def _texto_ou_none(valor):
    valor = (valor or "").strip() if isinstance(valor, str) else valor
    return valor or None