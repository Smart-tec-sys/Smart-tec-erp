from app.services.composicao_comercial import (
    calcular_itens, calcular_composicao, _preco_produto, _dinheiro,
    ITEM_PERSISTED_FIELDS, MULTIPLICADORES, MODELOS_POR_AREA,
)
from decimal import Decimal, ROUND_HALF_UP
from app.services.origem_comercial import CLIENTE_FINAL_CAMPOS, validar_origem_comercial
from app.services.condicoes_revenda import calcular_condicoes_revenda, textos_condicoes_revenda
from types import SimpleNamespace

from sqlalchemy import Integer, cast, func, text
from sqlalchemy.orm import Session, joinedload
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB, OrcamentoParcelaDB
from app.models.financeiro_cadastros import FormaPagamentoDB
from app.models.produto import ProdutoDB
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado

def _item_dict(i):
    # Recalcula área faturável para expor na resposta (backend é fonte de verdade)
    produto = None
    # Nota: produto não vem carregado no item, então recalculamos com os dados do item
    unidade = getattr(i, 'unidade', None)
    area_faturavel = calcular_area_faturavel(
        largura=float(i.largura or 0),
        altura=float(i.altura or 0),
        quantidade=int(i.quantidade or 0),
        unidade_venda=unidade,
    )
    return {
        "id": i.id,
        "tipo_item": i.tipo_item,
        "produto_id": i.produto_id,
        "descricao": i.descricao,
        "codigo_interno": i.codigo_interno,
        "grupo_tecnico": i.grupo_tecnico,
        "modelo_tecnico": i.modelo_tecnico,
        "unidade": i.unidade,
        "quantidade": float(i.quantidade or 0),
        "largura": float(i.largura or 0),
        "altura": float(i.altura or 0),
        "area": float(i.area or 0),
        "area_real_m2": float(area_faturavel.area_real_m2),
        "area_faturavel_m2": float(area_faturavel.area_faturavel_m2),
        "minimo_faturavel_aplicado": area_faturavel.minimo_faturavel_aplicado,
        "preco_unitario": float(i.preco_unitario or 0),
        "desconto": float(i.desconto or 0),
        "subtotal": float(i.subtotal or 0),
        "observacao_item": i.observacao_item,
        "material": i.material,
        "cor": i.cor,
        "acionamento": i.acionamento,
        "lado_comando": i.lado_comando,
        "calculo_producao_status": i.calculo_producao_status,
        "dados_tecnicos": i.dados_tecnicos,
    }

def _dict(o):
    parcelas = sorted(o.parcelas_pagamento or [], key=lambda parcela: parcela.numero)
    return {
        "id": o.id,
        "numero": o.numero,
        "cliente_id": o.cliente_id,
        "cliente_final_nome": o.cliente_final_nome,
        "cliente_final_documento": o.cliente_final_documento,
        "cliente_final_telefone": o.cliente_final_telefone,
        "cliente_final_email": o.cliente_final_email,
        "cliente_final_endereco": o.cliente_final_endereco,

        "cliente_nome": getattr(o.cliente, "nome", "") if o.cliente else "",
        "perfil_comercial": o.perfil_comercial,
        "status": o.status,
        "validade": o.validade,
        "observacao": o.observacao,
        "observacao_interna": o.observacao_interna,

        "total": float(o.total or 0),
        "desconto": float(o.desconto or 0),

        # Valor interno da empresa.
        "total_final": float(o.total_final or 0),

        "parceiro_id": o.parceiro_id,
        "percentual_parceiro": float(
            o.percentual_parceiro or 0
        ),

        "representante_id": o.representante_id,
        "vendedor_id": o.vendedor_id,
        "incluir_rt": bool(o.incluir_rt),
        "tipo_rt": o.tipo_rt,
        "percentual_rt": float(
            o.percentual_rt or 0
        ),
        "valor_rt": float(
            o.valor_rt or 0
        ),

        "incluir_taxa_bancaria": bool(
            o.incluir_taxa_bancaria
        ),
        "taxa_bancaria_percentual": float(
            o.taxa_bancaria_percentual or 0
        ),

        "valor_parceiro": float(
            o.valor_parceiro or 0
        ),
        "base_protegida": float(
            o.base_protegida or 0
        ),
        "valor_taxa_bancaria": float(
            o.valor_taxa_bancaria or 0
        ),
        "total_cliente_final": float(
            o.total_cliente_final or 0
        ),

        "pagamento_modalidade": o.pagamento_modalidade,
        "pagamento_numero_parcelas": o.pagamento_numero_parcelas,
        "pagamento_intervalo_dias": o.pagamento_intervalo_dias,
        "pagamento_primeiro_vencimento": o.pagamento_primeiro_vencimento,
        "pagamento_total": float(sum((parcela.valor for parcela in parcelas), Decimal("0"))),
        "pagamento_parcelas": [
            {
                "id": parcela.id,
                "numero": parcela.numero,
                "tipo": parcela.tipo,
                "valor": float(parcela.valor),
                "vencimento": parcela.vencimento,
                "forma_pagamento_id": parcela.forma_pagamento_id,
                "forma_pagamento_nome": parcela.forma_pagamento_nome,
            }
            for parcela in parcelas
        ],

        "criado_em": o.criado_em,
        "atualizado_em": o.atualizado_em,
        "itens": [
            _item_dict(i)
            for i in o.itens
        ],
    }

def listar(db:Session,tenant:TenantContext):
    q=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens),joinedload(OrcamentoDB.parcelas_pagamento)).filter(OrcamentoDB.empresa_id==require_tenant(tenant)).order_by(OrcamentoDB.id.desc())
    return [_dict(o) for o in q.all()]

def obter(db:Session,oid:int,tenant:TenantContext):
    o=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens),joinedload(OrcamentoDB.parcelas_pagamento)).filter(OrcamentoDB.id==oid,OrcamentoDB.empresa_id==require_tenant(tenant)).first()
    return _dict(o) if o else None

def _numero(db):
    db.execute(text("SELECT pg_advisory_xact_lock(2026082601)"))
    atual=db.query(func.max(cast(OrcamentoDB.numero,Integer))).scalar() or 0
    return str(max(int(atual)+1,1001))


def _preencher_pagamento(db, o, data, tenant_id):
    modalidade = data.pagamento_modalidade
    if modalidade is None and data.pagamento_parcelas is None:
        return
    parcelas = list(data.pagamento_parcelas or [])
    o.parcelas_pagamento.clear()
    if o.id is not None:
        db.flush()
    if modalidade is None:
        if parcelas:
            raise ValueError("Informe a modalidade da condição de pagamento.")
        o.pagamento_modalidade = None
        o.pagamento_numero_parcelas = None
        o.pagamento_intervalo_dias = None
        o.pagamento_primeiro_vencimento = None
        return

    quantidade = data.pagamento_numero_parcelas
    if quantidade is None or data.pagamento_primeiro_vencimento is None or data.pagamento_intervalo_dias is None:
        raise ValueError("Informe parcelas, primeiro vencimento e intervalo da condição de pagamento.")
    esperado = 1 if modalidade == "AVISTA" else 2 if modalidade == "ENTRADA_SALDO" else quantidade
    if quantidade != esperado or len(parcelas) != esperado:
        raise ValueError("A quantidade de parcelas não corresponde à modalidade selecionada.")
    if modalidade == "PARCELADO" and quantidade < 2:
        raise ValueError("Pagamento parcelado exige pelo menos duas parcelas.")
    if [parcela.numero for parcela in parcelas] != list(range(1, esperado + 1)):
        raise ValueError("As parcelas devem estar numeradas em sequência.")
    tipos_esperados = (["ENTRADA", "SALDO"] if modalidade == "ENTRADA_SALDO"
                       else ["PARCELA"] * esperado)
    if [parcela.tipo for parcela in parcelas] != tipos_esperados:
        raise ValueError("Os tipos das parcelas não correspondem à modalidade selecionada.")
    if parcelas[0].vencimento != data.pagamento_primeiro_vencimento:
        raise ValueError("O primeiro vencimento não corresponde à primeira parcela.")
    if any(atual.vencimento < anterior.vencimento for anterior, atual in zip(parcelas, parcelas[1:])):
        raise ValueError("Os vencimentos das parcelas devem estar em ordem crescente.")

    valores = [Decimal(parcela.valor).quantize(Decimal("0.01")) for parcela in parcelas]
    total_pagamento = sum(valores, Decimal("0"))
    total_comercial = Decimal(str(o.total_cliente_final or 0)).quantize(Decimal("0.01"))
    if total_pagamento != total_comercial:
        raise ValueError("A soma das parcelas deve ser igual ao total comercial definitivo.")

    formas = {}
    for forma_id in {parcela.forma_pagamento_id for parcela in parcelas}:
        forma = db.query(FormaPagamentoDB).filter(
            FormaPagamentoDB.id == forma_id,
            FormaPagamentoDB.empresa_id == tenant_id,
            FormaPagamentoDB.ativo.is_(True),
            FormaPagamentoDB.disponivel_para.in_(("RECEBER", "AMBOS")),
        ).first()
        if forma is None:
            raise ValueError("Forma de pagamento inválida para a empresa ativa.")
        formas[forma_id] = forma

    o.pagamento_modalidade = modalidade
    o.pagamento_numero_parcelas = quantidade
    o.pagamento_intervalo_dias = data.pagamento_intervalo_dias
    o.pagamento_primeiro_vencimento = data.pagamento_primeiro_vencimento
    for parcela, valor in zip(parcelas, valores):
        forma = formas[parcela.forma_pagamento_id]
        o.parcelas_pagamento.append(OrcamentoParcelaDB(
            empresa_id=tenant_id,
            numero=parcela.numero,
            tipo=parcela.tipo,
            valor=valor,
            vencimento=parcela.vencimento,
            forma_pagamento_id=forma.id,
            forma_pagamento_nome=forma.nome,
        ))

def _fill(db, o, data, tenant_id):
    cliente_final = {key: getattr(data, key) for key in CLIENTE_FINAL_CAMPOS}
    validar_origem_comercial(data.cliente_id, data.parceiro_id, cliente_final)
    for key, value in cliente_final.items():
        setattr(o, key, value)

    o.cliente_id = data.cliente_id
    o.perfil_comercial = data.perfil_comercial
    o.status = data.status
    o.validade = data.validade
    o.observacao = data.observacao
    o.observacao_interna = data.observacao_interna
    o.desconto = data.desconto
    calcular_itens(db, o, data, tenant_id, OrcamentoItemDB)
    # ================================================================
    # PARCEIRO
    # ================================================================
    percentual_parceiro = Decimal(
        str(data.percentual_parceiro or 0)
    )

    if percentual_parceiro < 0:
        raise ValueError(
            "Percentual do parceiro não pode ser negativo."
        )

    if data.parceiro_id is not None:
        parceiro = db.execute(
            text(
                """
                SELECT id
                FROM parceiros_comerciais
                WHERE id = :parceiro_id
                  AND empresa_id = :empresa_id
                  AND ativo = TRUE
                """
            ),
            {
                "parceiro_id": data.parceiro_id,
                "empresa_id": tenant_id,
            },
        ).first()

        if parceiro is None:
            raise ValueError(
                "Parceiro não encontrado ou inativo."
            )

    elif percentual_parceiro > 0:
        raise ValueError(
            "Selecione o parceiro para aplicar percentual."
        )

    o.parceiro_id = data.parceiro_id
    o.percentual_parceiro = percentual_parceiro

    # ================================================================
    # VENDEDOR SMART-TEC OPCIONAL
    # ================================================================
    if data.vendedor_id is not None:
        vendedor = db.execute(
            text(
                """
                SELECT id
                FROM funcionarios
                WHERE id = :vendedor_id
                  AND empresa_id = :empresa_id
                """
            ),
            {
                "vendedor_id": data.vendedor_id,
                "empresa_id": tenant_id,
            },
        ).first()

        if vendedor is None:
            raise ValueError(
                "Vendedor não encontrado para esta empresa."
            )

    o.vendedor_id = data.vendedor_id
    # ================================================================
    # REPRESENTANTE OPCIONAL
    # ================================================================
    if data.representante_id is not None:
        representante = db.execute(
            text(
                """
                SELECT id, parceiro_id
                FROM representantes
                WHERE id = :representante_id
                  AND empresa_id = :empresa_id
                  AND ativo = TRUE
                """
            ),
            {
                "representante_id": data.representante_id,
                "empresa_id": tenant_id,
            },
        ).first()

        if representante is None:
            raise ValueError(
                "Representante não encontrado ou inativo."
            )

        if data.parceiro_id is None:
            raise ValueError(
                "Selecione o parceiro para informar representante."
            )

        representante_parceiro_id = getattr(
            representante,
            "parceiro_id",
            None,
        )

        if (
            representante_parceiro_id is not None
            and representante_parceiro_id != data.parceiro_id
        ):
            raise ValueError(
                "O representante informado pertence a outro parceiro."
            )

    o.representante_id = data.representante_id

    calcular_composicao(o, data)
    _preencher_pagamento(db, o, data, tenant_id)

def criar(db,data,tenant:TenantContext):
    try:
        tenant_id=require_tenant(tenant); o=OrcamentoDB(numero=_numero(db),empresa_id=tenant_id); _fill(db,o,data,tenant_id); db.add(o); db.commit(); return obter(db,o.id,tenant)
    except Exception: db.rollback(); raise

def atualizar(db,oid,data,tenant:TenantContext):
    try:
        o=db.query(OrcamentoDB).filter(OrcamentoDB.id==oid,OrcamentoDB.empresa_id==require_tenant(tenant)).with_for_update().first()
        if not o:return None
        _fill(db,o,data,require_tenant(tenant)); db.commit(); return obter(db,o.id,tenant)
    except Exception: db.rollback(); raise


def atualizar_condicoes_revenda(db, oid, data, tenant: TenantContext):
    try:
        o = db.query(OrcamentoDB).filter(
            OrcamentoDB.id == oid, OrcamentoDB.empresa_id == require_tenant(tenant),
        ).with_for_update().first()
        if o is None:
            return None
        if (o.atualizado_em != data.atualizado_em_esperado
                or Decimal(str(o.total_final)) != Decimal(str(data.base_smarttec_esperada))
                or Decimal(str(o.total_cliente_final)) != Decimal(str(data.total_cliente_esperado))):
            raise ValueError("Orcamento alterado. Recarregue e confira os valores antes de salvar.")
        if not o.parceiro_id or o.status != "EM_ABERTO" or o.incluir_rt or o.incluir_taxa_bancaria:
            raise ValueError("Condicoes disponiveis somente para revenda em aberto, sem RT ou taxa fixa ativa.")
        itens = {item.id: item for item in o.itens}
        if not data.observacoes_itens.keys() <= itens.keys():
            raise ValueError("Observacao de item nao pertence ao orcamento.")
        c = calcular_condicoes_revenda(
            o.total_final, data.percentual_parceiro, data.desconto_pagamento_percentual,
            data.acrescimo_cartao_percentual, data.parcelas_cartao,
        )
        calcular_composicao(o, SimpleNamespace(
            desconto=o.desconto, parceiro_id=o.parceiro_id,
            percentual_parceiro=data.percentual_parceiro, incluir_rt=False,
            incluir_taxa_bancaria=False, taxa_bancaria_percentual=0,
        ))
        if o.total_final != c["base_smarttec"] or o.total_cliente_final != c["preco_cliente"]:
            raise ValueError("Base comercial inconsistente; nenhuma alteracao aplicada.")
        publico, interno = textos_condicoes_revenda(c)
        o.observacao = "\n\n".join(filter(None, [data.observacao_comercial.strip(), publico]))
        o.observacao_interna = "\n\n".join(filter(None, [data.observacao_interna.strip(), interno]))
        for item_id, observacao in data.observacoes_itens.items():
            itens[item_id].observacao_item = observacao
        db.commit()
        return obter(db, o.id, tenant)
    except Exception:
        db.rollback()
        raise

def remover(db,oid,tenant:TenantContext):
    try:
        o=db.query(OrcamentoDB).filter(OrcamentoDB.id==oid,OrcamentoDB.empresa_id==require_tenant(tenant)).first()
        if not o:return False
        db.delete(o); db.commit(); return True
    except Exception: db.rollback(); raise
