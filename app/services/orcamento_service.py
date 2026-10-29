from app.services.composicao_comercial import (
    calcular_itens, calcular_composicao, _preco_produto, _dinheiro,
    ITEM_PERSISTED_FIELDS, MULTIPLICADORES, MODELOS_POR_AREA,
)
from decimal import Decimal, ROUND_HALF_UP
from app.services.origem_comercial import CLIENTE_FINAL_CAMPOS, validar_origem_comercial

from sqlalchemy import Integer, cast, func, text
from sqlalchemy.orm import Session, joinedload
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
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

        "criado_em": o.criado_em,
        "atualizado_em": o.atualizado_em,
        "itens": [
            _item_dict(i)
            for i in o.itens
        ],
    }

def listar(db:Session,tenant:TenantContext):
    q=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens)).filter(OrcamentoDB.empresa_id==require_tenant(tenant)).order_by(OrcamentoDB.id.desc())
    return [_dict(o) for o in q.all()]

def obter(db:Session,oid:int,tenant:TenantContext):
    o=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens)).filter(OrcamentoDB.id==oid,OrcamentoDB.empresa_id==require_tenant(tenant)).first()
    return _dict(o) if o else None

def _numero(db):
    db.execute(text("SELECT pg_advisory_xact_lock(2026082601)"))
    atual=db.query(func.max(cast(OrcamentoDB.numero,Integer))).scalar() or 0
    return str(max(int(atual)+1,1001))

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

def remover(db,oid,tenant:TenantContext):
    try:
        o=db.query(OrcamentoDB).filter(OrcamentoDB.id==oid,OrcamentoDB.empresa_id==require_tenant(tenant)).first()
        if not o:return False
        db.delete(o); db.commit(); return True
    except Exception: db.rollback(); raise
