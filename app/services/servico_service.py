from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.exc import IntegrityError

from app.models.servico import ServicoDB
from app.schemas.servico import ServicoInput
from app.tenant.isolation import require_tenant


def _serializar(servico):
    return {
        "id": servico.id,
        "empresa_id": servico.empresa_id,
        "codigo": servico.codigo,
        "descricao": servico.descricao,
        "categoria": servico.categoria,
        "unidade": servico.unidade,
        "tipo_calculo": servico.tipo_calculo,
        "custo": float(servico.custo or 0),
        "preco_venda": float(servico.preco_venda or 0),
        "comissao": float(servico.comissao) if servico.comissao is not None else None,
        "observacoes": servico.observacoes,
        "situacao": servico.situacao,
        "faixas_altura": [
            {
                "altura_max_cm": float(faixa["altura_max_cm"]),
                "preco_unitario": float(faixa["preco_unitario"]),
            }
            for faixa in (servico.faixas_altura or [])
        ],
        "criado_em": servico.criado_em.isoformat() if servico.criado_em else None,
        "atualizado_em": servico.atualizado_em.isoformat() if servico.atualizado_em else None,
    }


def listar(db, tenant, busca=None, incluir_inativos=True):
    empresa_id = require_tenant(tenant)
    query = db.query(ServicoDB).filter(ServicoDB.empresa_id == empresa_id)
    if not incluir_inativos:
        query = query.filter(ServicoDB.situacao == "ATIVO")
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        query = query.filter(
            ServicoDB.codigo.ilike(padrao)
            | ServicoDB.descricao.ilike(padrao)
            | ServicoDB.categoria.ilike(padrao)
        )
    return [_serializar(item) for item in query.order_by(ServicoDB.descricao, ServicoDB.id).all()]


def obter(db, servico_id, tenant):
    empresa_id = require_tenant(tenant)
    servico = db.query(ServicoDB).filter(
        ServicoDB.id == servico_id,
        ServicoDB.empresa_id == empresa_id,
    ).first()
    return _serializar(servico) if servico else None


def _salvar(db, tenant, data, servico=None):
    empresa_id = require_tenant(tenant)
    payload = ServicoInput(**data.dict()).dict()
    if servico is None:
        servico = ServicoDB(empresa_id=empresa_id)
        db.add(servico)
    elif servico.empresa_id != empresa_id:
        return None

    servico.codigo = payload["codigo"]
    servico.descricao = payload["descricao"]
    servico.categoria = payload["categoria"]
    servico.unidade = payload["unidade"]
    servico.tipo_calculo = payload["tipo_calculo"]
    servico.custo = payload["custo"]
    servico.preco_venda = payload["preco_venda"]
    servico.comissao = payload["comissao"]
    servico.observacoes = payload["observacoes"]
    servico.situacao = payload["situacao"]
    servico.faixas_altura = [
        {
            "altura_max_cm": str(faixa.altura_max_cm),
            "preco_unitario": str(faixa.preco_unitario),
        }
        for faixa in payload["faixas_altura"]
    ]
    try:
        db.flush()
        db.commit()
        db.refresh(servico)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Já existe serviço com este código nesta empresa.") from exc
    except Exception:
        db.rollback()
        raise
    return _serializar(servico)


def criar(db, tenant, data):
    return _salvar(db, tenant, data)


def atualizar(db, servico_id, tenant, data):
    empresa_id = require_tenant(tenant)
    servico = db.query(ServicoDB).filter(
        ServicoDB.id == servico_id,
        ServicoDB.empresa_id == empresa_id,
    ).first()
    if servico is None:
        return None
    return _salvar(db, tenant, data, servico)


def calcular_preco_altura(servico, altura_cm):
    if servico.tipo_calculo != "FAIXA_ALTURA":
        return Decimal(str(servico.preco_venda or 0))
    try:
        altura = Decimal(str(altura_cm))
    except Exception as exc:
        raise ValueError("Informe a altura da peça em centímetros para calcular a lavagem.") from exc
    if not altura.is_finite() or altura <= 0:
        raise ValueError("A altura da peça deve ser positiva para calcular a lavagem.")
    for faixa in servico.faixas_altura or []:
        limite = Decimal(str(faixa["altura_max_cm"]))
        if altura <= limite:
            return Decimal(str(faixa["preco_unitario"])).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP,
            )
    raise ValueError("A tabela de lavagem não possui faixa para a altura informada.")
