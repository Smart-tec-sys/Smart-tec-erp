from decimal import Decimal, ROUND_HALF_UP

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
    return {"id":o.id,"numero":o.numero,"cliente_id":o.cliente_id,"cliente_nome":getattr(o.cliente,"nome","") if o.cliente else "","perfil_comercial":o.perfil_comercial,"status":o.status,"validade":o.validade,"observacao":o.observacao,"observacao_interna":o.observacao_interna,"total":float(o.total or 0),"desconto":float(o.desconto or 0),"total_final":float(o.total_final or 0),"criado_em":o.criado_em,"atualizado_em":o.atualizado_em,"itens":[_item_dict(i) for i in o.itens]}

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

ITEM_PERSISTED_FIELDS = {
    "tipo_item",
    "produto_id",
    "descricao",
    "codigo_interno",
    "grupo_tecnico",
    "modelo_tecnico",
    "unidade",
    "quantidade",
    "largura",
    "altura",
    "area",
    "preco_unitario",
    "desconto",
    "subtotal",
    "observacao_item",
    "material",
    "cor",
    "acionamento",
    "lado_comando",
    "calculo_producao_status",
    "dados_tecnicos",
}

MULTIPLICADORES = {"DECORADOR": Decimal("1.5"), "VAREJO": Decimal("2.0"), "CONSUMIDOR_FINAL": Decimal("2.5")}
MODELOS_POR_AREA = {"ROLO", "ROLÔ", "ROLO_MOTORIZADA", "ROLÔ MOTORIZADA", "DOUBLE_VISION", "DOUBLE VISION", "DOUBLE VISION MOTORIZADA", "ROMANA", "ROMANA MOTORIZADA", "ROMANA_TETO", "ROMANA DE TETO"}

def _dinheiro(valor):
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _preco_produto(produto, perfil):
    custo = Decimal(str(produto.custo_final or 0))
    if custo <= 0:
        custo = Decimal(str(produto.valor_custo or 0))
    if custo > 0:
        return (custo * MULTIPLICADORES[perfil]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _dinheiro(produto.valor_venda)

def _fill(db, o, data, tenant_id):
    for c in ["cliente_id","perfil_comercial","status","validade","observacao","observacao_interna","desconto"]: setattr(o,c,getattr(data,c))
    o.itens.clear()
    total = Decimal("0")
    for item in data.itens:
        valores = item.dict(include=ITEM_PERSISTED_FIELDS)
        if item.produto_id is not None:
            produto = db.query(ProdutoDB).filter(ProdutoDB.id == item.produto_id, ProdutoDB.empresa_id == tenant_id).first()
            if not produto:
                raise ValueError(f"Produto {item.produto_id} não encontrado para a empresa ativa")
            from app.services.romana_simulacao import tipo_romana, simular_romana, RomanaSimulacaoInput
            from app.services.double_vision_simulacao import _tipo_double_vision, simular_double_vision, DoubleVisionSimulacaoInput
            romana = tipo_romana(produto)
            if romana == 'MOTORIZADA':
                raise ValueError('Romana motorizada: cálculo técnico não liberado.')
            if romana == 'MANUAL':
                if not float(item.quantidade).is_integer():
                    raise ValueError('Romana manual exige quantidade inteira de peças.')
                simulacao = simular_romana(produto, RomanaSimulacaoInput(
                    produto_id=item.produto_id, largura=item.largura, altura=item.altura,
                    quantidade=int(item.quantidade), perfil_comercial=data.perfil_comercial,
                    desconto=item.desconto))
                if not simulacao['preco_disponivel']:
                    raise ValueError('Romana manual sem preço cadastrado disponível.')
                # Usa área real para o campo 'area' do banco; área faturável só para cálculo do subtotal
                valores.update(modelo_tecnico='ROMANA', area=simulacao['area_real_m2'],
                               preco_unitario=simulacao['preco_unitario'], subtotal=simulacao['subtotal'],
                               acionamento='MANUAL', calculo_producao_status='SIMULACAO_RECALCULADA')
                total += simulacao['subtotal']
                o.itens.append(OrcamentoItemDB(**valores))
                continue
            dv_tipo = _tipo_double_vision(produto)
            if dv_tipo == 'MANUAL':
                simulacao = simular_double_vision(produto, DoubleVisionSimulacaoInput(
                    produto_id=item.produto_id, largura=item.largura, altura=item.altura,
                    quantidade=int(item.quantidade), perfil_comercial=data.perfil_comercial,
                    desconto=item.desconto,
                    com_bando=False,
                    tem_validacao_tecido_fornecedor=False,
                ))
                if not simulacao['preco_disponivel']:
                    raise ValueError('Double Vision sem preço cadastrado disponível.')
                if not simulacao['permitido']:
                    raise ValueError(f'Double Vision: {simulacao["motivo_bloqueio"]}')
                if simulacao['estado_validacao'] == 'requer_validacao':
                    raise ValueError(f'Double Vision: {simulacao["motivo_bloqueio"]} — salve após confirmar compatibilidade tecido/fornecedor.')
                # Usa área real para o campo 'area' do banco; área faturável só para cálculo do subtotal
                valores.update(modelo_tecnico='DOUBLE VISION', area=simulacao['area_real_m2'],
                               preco_unitario=simulacao['preco_unitario'], subtotal=simulacao['subtotal'],
                               acionamento='MANUAL', calculo_producao_status='SIMULACAO_RECALCULADA')
                total += simulacao['subtotal']
                o.itens.append(OrcamentoItemDB(**valores))
                continue
            preco = _preco_produto(produto, data.perfil_comercial)
            modelo = str(item.modelo_tecnico or produto.modelo_tecnico or "").strip().upper()

            # Usa regra central de área faturável (mínimo 1,50 m² para produtos vendidos em M²)
            unidade_venda = getattr(produto, 'unidade_venda', None)
            area_faturavel: AreaFaturavelResultado = calcular_area_faturavel(
                largura=item.largura,
                altura=item.altura,
                quantidade=int(item.quantidade),
                unidade_venda=unidade_venda,
            )

            # Para modelos por área, usa área faturável; para outros, usa quantidade
            if modelo in MODELOS_POR_AREA:
                base = area_faturavel.area_faturavel_m2
            else:
                base = Decimal(str(item.quantidade))

            subtotal = max(Decimal("0"), (base * preco) - Decimal(str(item.desconto or 0)))
            valores["preco_unitario"] = preco
            valores["subtotal"] = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Salva também a área real e faturável para auditoria
            valores["area"] = float(area_faturavel.area_real_m2)
        else:
            subtotal = max(Decimal("0"), Decimal(str(item.quantidade)) * Decimal(str(item.preco_unitario)) - Decimal(str(item.desconto or 0)))
            valores["subtotal"] = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += Decimal(str(valores["subtotal"]))
        o.itens.append(OrcamentoItemDB(**valores))
    o.total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    o.total_final = max(Decimal("0"), o.total - Decimal(str(data.desconto or 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
