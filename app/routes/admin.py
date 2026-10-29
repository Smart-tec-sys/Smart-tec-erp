from decimal import Decimal
import json
from calendar import monthrange
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.admin.dependencies import (
    get_current_platform_member,
    require_platform_permission,
)
from app.admin.service import PlatformMemberContext
from app.database import get_db
from app.admin import subscriptions
from app.admin.payment_methods import (AdminPaymentMethodCreate, list_payment_methods, create_payment_method, resolve_order_payment_method)


router = APIRouter()


class AdminTrialStartInput(BaseModel):
    plano_id: int | None = None
    dias: int = Field(default=7, ge=1, le=30)
    observacoes: str | None = None


class AdminSubscriptionActivateInput(BaseModel):
    plano_id: int
    periodicidade: str | None = None
    valor: Decimal | None = Field(default=None, ge=0)
    renovacao_automatica: bool = False
    observacoes: str | None = None


class AdminModuleActivateInput(BaseModel):
    origem: str
    valor: Decimal | None = Field(default=None, ge=0)
    periodicidade: str | None = None
    data_fim: date | None = None
    observacoes: str | None = None


class AdminModuleOrderCreateInput(BaseModel):
    modulo_id: int
    valor: Decimal = Field(ge=0)
    periodicidade: str
    forma_pagamento_id: int | None = Field(default=None, gt=0)
    forma_pagamento: str | None = None
    observacoes: str | None = None


class AdminModuleOrderStatusInput(BaseModel):
    status: str


def _audit_admin(
    db: Session,
    *,
    member: PlatformMemberContext,
    empresa_id: int | None,
    acao: str,
    recurso: str,
    recurso_id: str | int | None,
    detalhes: dict | None = None,
):
    db.execute(
        text("""
            INSERT INTO auditoria_plataforma (
                equipe_id,
                usuario_id,
                empresa_afetada_id,
                acao,
                recurso,
                recurso_id,
                detalhes
            )
            VALUES (
                :equipe_id,
                :usuario_id,
                :empresa_id,
                :acao,
                :recurso,
                :recurso_id,
                CAST(:detalhes AS JSONB)
            )
        """),
        {
            "equipe_id": member.equipe_id,
            "usuario_id": member.usuario_id,
            "empresa_id": empresa_id,
            "acao": acao,
            "recurso": recurso,
            "recurso_id": (
                str(recurso_id)
                if recurso_id is not None
                else None
            ),
            "detalhes": json.dumps(
                detalhes or {},
                ensure_ascii=False,
                default=str,
            ),
        },
    )


def _require_admin_empresa(
    db: Session,
    empresa_id: int,
):
    row = db.execute(
        text("""
            SELECT
                id,
                nome,
                nome_fantasia,
                status
            FROM empresas
            WHERE id = :empresa_id
        """),
        {"empresa_id": empresa_id},
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="empresa não encontrada",
        )

    return row


def _next_due_date(
    inicio: date,
    periodicidade: str,
) -> date:
    periodicidade = periodicidade.upper()

    if periodicidade == "ANUAL":
        try:
            return inicio.replace(
                year=inicio.year + 1
            )
        except ValueError:
            return inicio.replace(
                year=inicio.year + 1,
                day=28,
            )

    if periodicidade == "MENSAL":
        if inicio.month == 12:
            year = inicio.year + 1
            month = 1
        else:
            year = inicio.year
            month = inicio.month + 1

        day = min(
            inicio.day,
            monthrange(year, month)[1],
        )

        return date(year, month, day)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="periodicidade deve ser MENSAL ou ANUAL",
    )


def _activate_plan_modules(
    db: Session,
    *,
    empresa_id: int,
    assinatura_id: int,
    plano_id: int,
    data_fim: date | None,
):
    return subscriptions.activate_plan_modules(
        db, empresa_id=empresa_id, assinatura_id=assinatura_id,
        plano_id=plano_id, data_fim=data_fim,
    )


@router.get("/me")
def admin_me(
    member: Annotated[
        PlatformMemberContext,
        Depends(get_current_platform_member),
    ],
):
    return {
        "user": {
            "id": member.usuario_id,
            "nome": member.nome,
            "email": member.email,
        },
        "equipe": {
            "id": member.equipe_id,
            "cargo_exibicao": member.cargo_exibicao,
            "funcao": {
                "id": member.funcao_id,
                "codigo": member.funcao_codigo,
                "nome": member.funcao_nome,
                "nivel": member.nivel,
            },
            "is_owner": member.is_platform_owner,
            "is_administrator": member.is_platform_administrator,
        },
        "permissions": sorted(member.permissions),
    }


@router.get("/overview")
def admin_overview(
    member: Annotated[
        PlatformMemberContext,
        Depends(require_platform_permission("EMPRESAS_VER")),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    hoje = date.today()
    limite_trial = hoje + timedelta(days=7)
    limite_renovacao = hoje + timedelta(days=10)

    empresas = db.execute(
        text("""
            SELECT COUNT(*)
            FROM empresas
            WHERE status = 'ATIVA'
        """)
    ).scalar_one()

    trials_ativos = db.execute(
        text("""
            SELECT COUNT(*)
            FROM assinaturas_saas
            WHERE status = 'TRIAL'
              AND (
                data_fim_trial IS NULL
                OR data_fim_trial >= :hoje
              )
        """),
        {"hoje": hoje},
    ).scalar_one()

    trials_encerrando = db.execute(
        text("""
            SELECT COUNT(*)
            FROM assinaturas_saas
            WHERE status = 'TRIAL'
              AND data_fim_trial
                  BETWEEN :hoje AND :limite
        """),
        {
            "hoje": hoje,
            "limite": limite_trial,
        },
    ).scalar_one()

    renovacoes = db.execute(
        text("""
            SELECT COUNT(*)
            FROM assinaturas_saas
            WHERE status IN (
                'ATIVA',
                'PROXIMA_VENCIMENTO'
            )
              AND data_vencimento
                  BETWEEN :hoje AND :limite
        """),
        {
            "hoje": hoje,
            "limite": limite_renovacao,
        },
    ).scalar_one()

    pedidos = db.execute(
        text("""
            SELECT COUNT(*)
            FROM pedidos_modulos_saas
            WHERE status IN (
                'SOLICITADO',
                'EM_ANALISE',
                'AGUARDANDO_PAGAMENTO',
                'PAGO'
            )
        """)
    ).scalar_one()

    chamados = db.execute(
        text("""
            SELECT COUNT(*)
            FROM chamados_suporte_saas
            WHERE status IN (
                'ABERTO',
                'EM_ANALISE',
                'AGUARDANDO_CLIENTE',
                'EM_CORRECAO'
            )
        """)
    ).scalar_one()

    pagamentos = db.execute(
        text("""
            SELECT COUNT(*)
            FROM pagamentos_saas
            WHERE status IN (
                'PENDENTE',
                'PROCESSANDO',
                'ATRASADO'
            )
        """)
    ).scalar_one()

    notas = db.execute(
        text("""
            SELECT COUNT(*)
            FROM notas_fiscais_saas
            WHERE status IN (
                'PENDENTE',
                'PROCESSANDO',
                'ERRO'
            )
        """)
    ).scalar_one()

    return {
        "empresas_ativas": empresas,
        "trials_ativos": trials_ativos,
        "trials_encerrando_em_7_dias": trials_encerrando,
        "renovacoes_em_10_dias": renovacoes,
        "pedidos_modulos_pendentes": pedidos,
        "chamados_abertos": chamados,
        "pagamentos_pendentes": pagamentos,
        "notas_fiscais_pendentes": notas,
    }


@router.get("/empresas")
def admin_empresas(
    member: Annotated[
        PlatformMemberContext,
        Depends(require_platform_permission("EMPRESAS_VER")),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    rows = db.execute(
        text("""
            SELECT
                e.id,
                e.nome,
                e.nome_fantasia,
                e.documento,
                e.status,
                e.slug,
                e.logo_url,
                e.criado_em,

                (
                    SELECT COUNT(*)
                    FROM empresa_usuarios eu
                    WHERE eu.empresa_id = e.id
                      AND eu.ativo = TRUE
                ) AS usuarios_ativos,

                (
                    SELECT COUNT(*)
                    FROM empresa_modulos_saas em
                    WHERE em.empresa_id = e.id
                      AND em.status = 'ATIVO'
                ) AS modulos_ativos,

                (
                    SELECT a.status
                    FROM assinaturas_saas a
                    WHERE a.empresa_id = e.id
                    ORDER BY a.id DESC
                    LIMIT 1
                ) AS assinatura_status,

                (
                    SELECT a.data_vencimento
                    FROM assinaturas_saas a
                    WHERE a.empresa_id = e.id
                    ORDER BY a.id DESC
                    LIMIT 1
                ) AS data_vencimento,

                (
                    SELECT a.data_fim_trial
                    FROM assinaturas_saas a
                    WHERE a.empresa_id = e.id
                    ORDER BY a.id DESC
                    LIMIT 1
                ) AS data_fim_trial,

                (
                    SELECT COUNT(*)
                    FROM chamados_suporte_saas c
                    WHERE c.empresa_id = e.id
                      AND c.status IN (
                        'ABERTO',
                        'EM_ANALISE',
                        'AGUARDANDO_CLIENTE',
                        'EM_CORRECAO'
                      )
                ) AS chamados_abertos

            FROM empresas e
            ORDER BY
                CASE WHEN e.status = 'ATIVA' THEN 0 ELSE 1 END,
                COALESCE(e.nome_fantasia, e.nome),
                e.id
        """)
    ).mappings().all()

    return {
        "items": [
            dict(row)
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/empresas/{empresa_id}")
def admin_empresa_detalhe(
    empresa_id: int,
    member: Annotated[
        PlatformMemberContext,
        Depends(require_platform_permission("EMPRESAS_VER")),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    empresa = db.execute(
        text("""
            SELECT
                id,
                nome,
                nome_fantasia,
                documento,
                status,
                slug,
                logo_url,
                configuracoes,
                criado_em,
                atualizado_em
            FROM empresas
            WHERE id = :empresa_id
        """),
        {"empresa_id": empresa_id},
    ).mappings().first()

    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="empresa não encontrada",
        )

    usuarios = db.execute(
        text("""
            SELECT
                u.id,
                u.nome,
                u.email,
                u.status,
                u.foto_url,
                eu.papel,
                eu.ativo
            FROM empresa_usuarios eu
            JOIN usuarios u
              ON u.id = eu.usuario_id
            WHERE eu.empresa_id = :empresa_id
            ORDER BY
                CASE eu.papel
                    WHEN 'OWNER' THEN 0
                    WHEN 'ADMIN' THEN 1
                    ELSE 2
                END,
                u.nome
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    assinatura = db.execute(
        text("""
            SELECT
                a.id,
                a.status,
                a.periodicidade,
                a.plano_id,
                a.forma_pagamento_id,
                fp.nome AS forma_pagamento_nome,
                a.data_inicio_trial,
                a.data_fim_trial,
                a.data_inicio_assinatura,
                a.data_vencimento,
                a.renovacao_automatica,
                a.valor,
                a.dias_aviso_vencimento,
                a.observacoes,
                p.codigo AS plano_codigo,
                p.nome AS plano_nome,
                p.produto AS plano_produto
            FROM assinaturas_saas a
            LEFT JOIN planos_saas p
              ON p.id = a.plano_id
            LEFT JOIN formas_pagamento fp ON fp.id = a.forma_pagamento_id
            WHERE a.empresa_id = :empresa_id
            ORDER BY a.id DESC
            LIMIT 1
        """),
        {"empresa_id": empresa_id},
    ).mappings().first()

    modulos = db.execute(
        text("""
            SELECT
                em.id,
                em.assinatura_id,
                m.codigo,
                m.nome,
                m.produto,
                em.origem,
                em.status,
                em.data_inicio,
                em.data_fim,
                em.valor,
                em.periodicidade,
                em.observacoes
            FROM empresa_modulos_saas em
            JOIN modulos_saas m
              ON m.id = em.modulo_id
            WHERE em.empresa_id = :empresa_id
            ORDER BY
                CASE em.status
                    WHEN 'ATIVO' THEN 0
                    WHEN 'PENDENTE' THEN 1
                    ELSE 2
                END,
                m.nome
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    pedidos = db.execute(
        text("""
            SELECT
                pm.id,
                m.nome AS modulo_nome,
                pm.status,
                pm.valor,
                pm.periodicidade,
                pm.data_pedido,
                pm.data_aprovacao,
                pm.data_ativacao,
                pm.forma_pagamento,
                pm.forma_pagamento_id,
                COALESCE(fp.nome,pm.forma_pagamento) AS forma_pagamento_nome,
                pm.observacoes,
                pm.responsavel_equipe_id,
                u.nome AS responsavel_nome
            FROM pedidos_modulos_saas pm
            LEFT JOIN formas_pagamento fp ON fp.id=pm.forma_pagamento_id
            JOIN modulos_saas m
              ON m.id = pm.modulo_id
            LEFT JOIN plataforma_equipe pe
              ON pe.id = pm.responsavel_equipe_id
            LEFT JOIN usuarios u
              ON u.id = pe.usuario_id
            WHERE pm.empresa_id = :empresa_id
            ORDER BY pm.id DESC
            LIMIT 20
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    pagamentos = db.execute(
        text("""
            SELECT
                p.id,
                p.assinatura_id,
                p.pedido_modulo_id,
                p.ciclo_inicio,
                p.ciclo_fim,
                p.tipo,
                p.status,
                p.valor,
                p.vencimento,
                p.pago_em,
                p.forma_pagamento,
                p.forma_pagamento_id,
                COALESCE(fp.nome,p.forma_pagamento) AS forma_pagamento_nome,
                p.referencia_externa,
                p.observacoes,
                p.criado_em,
                p.atualizado_em
            FROM pagamentos_saas p
            LEFT JOIN formas_pagamento fp ON fp.id=p.forma_pagamento_id
            WHERE p.empresa_id = :empresa_id
            ORDER BY p.id DESC
            LIMIT 20
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    cobrancas_assinatura = db.execute(
        text("""
            SELECT
                p.id,
                p.assinatura_id,
                p.pedido_modulo_id,
                p.ciclo_inicio,
                p.ciclo_fim,
                p.tipo,
                p.status,
                p.valor,
                p.vencimento,
                p.pago_em,
                p.forma_pagamento,
                p.forma_pagamento_id,
                COALESCE(fp.nome,p.forma_pagamento) AS forma_pagamento_nome,
                p.referencia_externa,
                p.observacoes,
                p.criado_em,
                p.atualizado_em
            FROM pagamentos_saas p
            LEFT JOIN formas_pagamento fp ON fp.id=p.forma_pagamento_id
            WHERE p.empresa_id = :empresa_id AND p.tipo = 'ASSINATURA'
            ORDER BY p.id DESC
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    notas = db.execute(
        text("""
            SELECT
                id,
                assinatura_id,
                pagamento_id,
                tipo_documento,
                status,
                numero,
                serie,
                valor_servico,
                valor_desconto,
                valor_total,
                data_emissao,
                descricao_servico,
                referencia_externa,
                protocolo,
                pdf_url,
                xml_url,
                erro_codigo,
                erro_mensagem,
                criado_em,
                atualizado_em
            FROM notas_fiscais_saas
            WHERE empresa_id = :empresa_id
            ORDER BY id DESC
            LIMIT 20
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    chamados = db.execute(
        text("""
            SELECT
                id,
                codigo,
                status,
                prioridade,
                titulo,
                pagina,
                request_id,
                criado_em,
                atualizado_em,
                resolvido_em
            FROM chamados_suporte_saas
            WHERE empresa_id = :empresa_id
            ORDER BY id DESC
            LIMIT 30
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    comercial = db.execute(
        text("""
            SELECT
                ac.id,
                ac.tipo,
                ac.status_contato,
                ac.ultimo_contato,
                ac.proximo_contato,
                ac.observacao,
                u.nome AS responsavel_nome
            FROM acompanhamentos_comerciais_saas ac
            LEFT JOIN plataforma_equipe pe
              ON pe.id = ac.responsavel_equipe_id
            LEFT JOIN usuarios u
              ON u.id = pe.usuario_id
            WHERE ac.empresa_id = :empresa_id
            ORDER BY ac.id DESC
            LIMIT 30
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    historico = db.execute(
        text("""
            SELECT
                ap.id,
                ap.acao,
                ap.recurso,
                ap.recurso_id,
                ap.detalhes,
                ap.request_id,
                ap.criado_em,
                u.nome AS usuario_nome
            FROM auditoria_plataforma ap
            LEFT JOIN usuarios u
              ON u.id = ap.usuario_id
            WHERE ap.empresa_afetada_id = :empresa_id
            ORDER BY ap.id DESC
            LIMIT 100
        """),
        {"empresa_id": empresa_id},
    ).mappings().all()

    resumo = db.execute(
        text("""
            SELECT
                (
                    SELECT COUNT(*)
                    FROM chamados_suporte_saas c
                    WHERE c.empresa_id = :empresa_id
                      AND c.status IN (
                        'ABERTO',
                        'EM_ANALISE',
                        'AGUARDANDO_CLIENTE',
                        'EM_CORRECAO'
                      )
                ) AS chamados_abertos,

                (
                    SELECT COUNT(*)
                    FROM pagamentos_saas p
                    WHERE p.empresa_id = :empresa_id
                      AND p.status IN (
                        'PENDENTE',
                        'PROCESSANDO',
                        'ATRASADO'
                      )
                ) AS pagamentos_pendentes,

                (
                    SELECT COUNT(*)
                    FROM notas_fiscais_saas nf
                    WHERE nf.empresa_id = :empresa_id
                      AND nf.status IN (
                        'PENDENTE',
                        'PROCESSANDO',
                        'ERRO'
                      )
                ) AS notas_pendentes,

                (
                    SELECT COUNT(*)
                    FROM empresa_modulos_saas em
                    WHERE em.empresa_id = :empresa_id
                      AND em.status = 'ATIVO'
                ) AS modulos_ativos
        """),
        {"empresa_id": empresa_id},
    ).mappings().one()

    return {
        "empresa": dict(empresa),
        "resumo": dict(resumo),
        "usuarios": [dict(row) for row in usuarios],
        "assinatura": dict(assinatura) if assinatura else None,
        "modulos": [dict(row) for row in modulos],
        "pedidos_modulos": [dict(row) for row in pedidos],
        "pagamentos": [dict(row) for row in pagamentos],
        "cobrancas_assinatura": [dict(row) for row in cobrancas_assinatura],
        "notas_fiscais": [dict(row) for row in notas],
        "chamados": [dict(row) for row in chamados],
        "acompanhamento_comercial": [
            dict(row)
            for row in comercial
        ],
        "historico": [
            dict(row)
            for row in historico
        ],
    }


# ============================================================
# CATALOGO ADMINISTRATIVO
# ============================================================

@router.get("/catalogo/planos")
def admin_planos(
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "ASSINATURAS_VER"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    rows = db.execute(
        text("""
            SELECT
                id,
                codigo,
                nome,
                produto,
                periodicidade,
                valor,
                dias_trial,
                ativo,
                descricao
            FROM planos_saas
            ORDER BY ativo DESC, produto, nome
        """)
    ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "total": len(rows),
    }


@router.get("/catalogo/modulos")
def admin_modulos_catalogo(
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "MODULOS_VER"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    rows = db.execute(
        text("""
            SELECT
                id,
                codigo,
                nome,
                produto,
                descricao,
                ativo
            FROM modulos_saas
            ORDER BY produto, nome
        """)
    ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "total": len(rows),
    }


# ============================================================
# TRIAL
# ============================================================

@router.post("/empresas/{empresa_id}/trial")
def admin_iniciar_trial(
    empresa_id: int,
    payload: AdminTrialStartInput,
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "ASSINATURAS_EDITAR"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    try:
        # Mesma trava dos contratos; permanece até commit ou rollback.
        subscriptions._company(db, empresa_id)

        existente = db.execute(
            text("""
                SELECT id, status
                FROM assinaturas_saas
                WHERE empresa_id = :empresa_id
                  AND status IN :estados
                ORDER BY id DESC
                LIMIT 1
            """).bindparams(bindparam("estados", expanding=True)),
            {
                "empresa_id": empresa_id,
                "estados": subscriptions.LIVE_CONTRACT_STATUSES,
            },
        ).mappings().first()

        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Empresa já possui assinatura vigente; utilize o contrato existente.",
            )

        plano = None

        if payload.plano_id is not None:
            plano = db.execute(
                text("""
                    SELECT
                        id,
                        codigo,
                        nome,
                        periodicidade,
                        dias_trial,
                        ativo
                    FROM planos_saas
                    WHERE id = :id
                """),
                {"id": payload.plano_id},
            ).mappings().first()

            if plano is None or not plano["ativo"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="plano ativo não encontrado",
                )

            # Recusa somente zero explicito; configuracoes legadas desconhecidas preservam o fluxo.
            if type(plano.get("dias_trial")) is int and plano["dias_trial"] == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Trial não permitido para este plano.",
                )

        hoje = date.today()
        fim = hoje + timedelta(days=payload.dias)

        assinatura_id = db.execute(
            text("""
                INSERT INTO assinaturas_saas (
                    empresa_id,
                    plano_id,
                    status,
                    periodicidade,
                    data_inicio_trial,
                    data_fim_trial,
                    dias_aviso_vencimento,
                    observacoes
                )
                VALUES (
                    :empresa_id,
                    :plano_id,
                    'TRIAL',
                    :periodicidade,
                    :inicio,
                    :fim,
                    10,
                    :observacoes
                )
                RETURNING id
            """),
            {
                "empresa_id": empresa_id,
                "plano_id": (
                    plano["id"]
                    if plano
                    else None
                ),
                "periodicidade": (
                    plano["periodicidade"]
                    if plano
                    else None
                ),
                "inicio": hoje,
                "fim": fim,
                "observacoes": payload.observacoes,
            },
        ).scalar_one()

        if plano:
            modules = db.execute(
                text("""
                    SELECT modulo_id
                    FROM plano_modulos_saas
                    WHERE plano_id = :plano_id
                      AND incluido = TRUE
                """),
                {"plano_id": plano["id"]},
            ).scalars().all()

            for modulo_id in modules:
                existing = db.execute(
                    text("""
                        SELECT id
                        FROM empresa_modulos_saas
                        WHERE empresa_id = :empresa_id
                          AND modulo_id = :modulo_id
                          AND status IN (
                            'ATIVO',
                            'PENDENTE'
                          )
                        LIMIT 1
                    """),
                    {
                        "empresa_id": empresa_id,
                        "modulo_id": modulo_id,
                    },
                ).scalar()

                if not existing:
                    db.execute(
                        text("""
                            INSERT INTO empresa_modulos_saas (
                                empresa_id,
                                modulo_id,
                                assinatura_id,
                                origem,
                                status,
                                data_inicio,
                                data_fim,
                                periodicidade
                            )
                            VALUES (
                                :empresa_id,
                                :modulo_id,
                                :assinatura_id,
                                'TRIAL',
                                'ATIVO',
                                :inicio,
                                :fim,
                                'CORTESIA'
                            )
                        """),
                        {
                            "empresa_id": empresa_id,
                            "modulo_id": modulo_id,
                            "assinatura_id": assinatura_id,
                            "inicio": hoje,
                            "fim": fim,
                        },
                    )

        _audit_admin(
            db,
            member=member,
            empresa_id=empresa_id,
            acao="TRIAL_INICIADO",
            recurso="assinaturas_saas",
            recurso_id=assinatura_id,
            detalhes={
                "dias": payload.dias,
                "data_inicio": hoje,
                "data_fim": fim,
                "plano_id": payload.plano_id,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "assinatura_id": assinatura_id,
        "status": "TRIAL",
        "data_inicio_trial": hoje,
        "data_fim_trial": fim,
    }


# ============================================================
# ATIVAR ASSINATURA
# ============================================================

@router.post("/empresas/{empresa_id}/assinatura/ativar")
def admin_ativar_assinatura(
    empresa_id: int,
    payload: AdminSubscriptionActivateInput,
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "ASSINATURAS_EDITAR"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    raise HTTPException(
        status_code=409,
        detail="Ativação direta substituída pelo ciclo antecipado: prepare o contrato, gere a cobrança e confirme o pagamento.",
    )


# ============================================================
# ATIVAR MODULO
# ============================================================

@router.post("/empresas/{empresa_id}/modulos/{modulo_id}/ativar")
def admin_ativar_modulo(
    empresa_id: int,
    modulo_id: int,
    payload: AdminModuleActivateInput,
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "MODULOS_ATIVAR"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    _require_admin_empresa(
        db,
        empresa_id,
    )

    modulo = db.execute(
        text("""
            SELECT
                id,
                codigo,
                nome,
                ativo
            FROM modulos_saas
            WHERE id = :id
        """),
        {"id": modulo_id},
    ).mappings().first()

    if modulo is None or not modulo["ativo"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="módulo ativo não encontrado",
        )

    origem = payload.origem.upper()

    if origem != "CORTESIA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ativação direta disponível somente para CORTESIA. AVULSO deve seguir Pedido; PLANO e TRIAL são gerenciados pela assinatura e pelo trial.",
        )

    if not member.has_permission("MODULOS_CORTESIA"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sem permissão para conceder cortesia",
        )

    if payload.valor not in (None, Decimal("0")) or payload.periodicidade not in (None, "CORTESIA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cortesia não possui valor comercial e deve usar periodicidade CORTESIA.",
        )
    if payload.data_fim is not None and payload.data_fim < date.today():
        raise HTTPException(status_code=400, detail="Data fim da cortesia não pode anteceder a data de início.")

    periodicidade = "CORTESIA"
    effective_data_fim = payload.data_fim

    try:
        existente = db.execute(
            text("""
                SELECT id
                FROM empresa_modulos_saas
                WHERE empresa_id = :empresa_id
                  AND modulo_id = :modulo_id
                  AND status IN (
                    'ATIVO',
                    'PENDENTE',
                    'SUSPENSO'
                  )
                ORDER BY id DESC
                LIMIT 1
            """),
            {
                "empresa_id": empresa_id,
                "modulo_id": modulo_id,
            },
        ).scalar()

        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="empresa já possui vínculo vigente ou suspenso para este módulo",
            )

        registro_id = db.execute(
            text("""
                INSERT INTO empresa_modulos_saas (
                    empresa_id,
                    modulo_id,
                    origem,
                    status,
                    data_inicio,
                    data_fim,
                    valor,
                    periodicidade,
                    observacoes
                )
                VALUES (
                    :empresa_id,
                    :modulo_id,
                    :origem,
                    'ATIVO',
                    CURRENT_DATE,
                    :data_fim,
                    :valor,
                    :periodicidade,
                    :observacoes
                )
                RETURNING id
            """),
            {
                "empresa_id": empresa_id,
                "modulo_id": modulo_id,
                "origem": origem,
                "data_fim": effective_data_fim,
                "valor": payload.valor,
                "periodicidade": periodicidade,
                "observacoes": payload.observacoes,
            },
        ).scalar_one()

        _audit_admin(
            db,
            member=member,
            empresa_id=empresa_id,
            acao="MODULO_ATIVADO",
            recurso="empresa_modulos_saas",
            recurso_id=registro_id,
            detalhes={
                "modulo_id": modulo_id,
                "modulo": modulo["nome"],
                "origem": origem,
                "valor": payload.valor,
                "periodicidade": periodicidade,
                "data_fim": effective_data_fim,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "registro_id": registro_id,
        "modulo_id": modulo_id,
        "modulo": modulo["nome"],
        "status": "ATIVO",
        "origem": origem,
    }


# ============================================================
# CANCELAR MODULO
# ============================================================

@router.post("/empresas/{empresa_id}/modulos/{modulo_id}/cancelar")
def admin_cancelar_modulo(
    empresa_id: int,
    modulo_id: int,
    member: Annotated[
        PlatformMemberContext,
        Depends(
            require_platform_permission(
                "MODULOS_CANCELAR"
            )
        ),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    _require_admin_empresa(
        db,
        empresa_id,
    )

    registro = db.execute(
        text("""
            SELECT
                em.id,
                em.origem,
                m.nome
            FROM empresa_modulos_saas em
            JOIN modulos_saas m
              ON m.id = em.modulo_id
            WHERE em.empresa_id = :empresa_id
              AND em.modulo_id = :modulo_id
              AND em.status IN (
                'ATIVO',
                'PENDENTE'
              )
            ORDER BY em.id DESC
            LIMIT 1
        """),
        {
            "empresa_id": empresa_id,
            "modulo_id": modulo_id,
        },
    ).mappings().first()

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="módulo ativo não encontrado para a empresa",
        )

    if registro["origem"] in {"PLANO", "TRIAL"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Este módulo é gerenciado pela assinatura." if registro["origem"] == "PLANO"
                    else "Este acesso é gerenciado pelo trial; não pode ser cancelado isoladamente."),
        )

    try:
        db.execute(
            text("""
                UPDATE empresa_modulos_saas
                SET
                    status = 'CANCELADO',
                    data_fim = CURRENT_DATE,
                    atualizado_em = NOW()
                WHERE id = :id
            """),
            {"id": registro["id"]},
        )

        _audit_admin(
            db,
            member=member,
            empresa_id=empresa_id,
            acao="MODULO_CANCELADO",
            recurso="empresa_modulos_saas",
            recurso_id=registro["id"],
            detalhes={
                "modulo_id": modulo_id,
                "modulo": registro["nome"],
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "registro_id": registro["id"],
        "modulo_id": modulo_id,
        "status": "CANCELADO",
    }




# ============================================================
# PEDIDOS DE MODULOS
# ============================================================

@router.post("/empresas/{empresa_id}/pedidos-modulos")
def admin_criar_pedido_modulo(
    empresa_id: int,
    payload: AdminModuleOrderCreateInput,
    member: Annotated[
        PlatformMemberContext,
        Depends(get_current_platform_member),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    if not member.has_permission("MODULOS_ATIVAR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sem permissão para registrar pedido de módulo",
        )

    _require_admin_empresa(
        db,
        empresa_id,
    )

    periodicidade = payload.periodicidade.upper()

    if periodicidade not in {
        "MENSAL",
        "ANUAL",
        "UNICO",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "periodicidade deve ser "
                "MENSAL, ANUAL ou UNICO"
            ),
        )

    modulo = db.execute(
        text("""
            SELECT
                id,
                codigo,
                nome,
                ativo
            FROM modulos_saas
            WHERE id = :modulo_id
        """),
        {
            "modulo_id": payload.modulo_id,
        },
    ).mappings().first()

    if modulo is None or not modulo["ativo"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="módulo SaaS ativo não encontrado",
        )

    modulo_ativo = db.execute(
        text("""
            SELECT id
            FROM empresa_modulos_saas
            WHERE empresa_id = :empresa_id
              AND modulo_id = :modulo_id
              AND status IN (
                  'ATIVO',
                  'PENDENTE',
                  'SUSPENSO'
              )
            ORDER BY id DESC
            LIMIT 1
        """),
        {
            "empresa_id": empresa_id,
            "modulo_id": payload.modulo_id,
        },
    ).scalar()

    if modulo_ativo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="empresa já possui vínculo vigente ou suspenso para este módulo",
        )

    pedido_existente = db.execute(
        text("""
            SELECT id
            FROM pedidos_modulos_saas
            WHERE empresa_id = :empresa_id
              AND modulo_id = :modulo_id
              AND status IN (
                  'SOLICITADO',
                  'EM_ANALISE',
                  'AGUARDANDO_PAGAMENTO',
                  'PAGO'
              )
            ORDER BY id DESC
            LIMIT 1
        """),
        {
            "empresa_id": empresa_id,
            "modulo_id": payload.modulo_id,
        },
    ).scalar()

    if pedido_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "já existe um pedido em andamento "
                "para este módulo"
            ),
        )

    forma_pagamento_id, forma_pagamento = resolve_order_payment_method(
        db, payload.forma_pagamento_id, payload.forma_pagamento,
    )

    try:
        pedido_id = db.execute(
            text("""
                INSERT INTO pedidos_modulos_saas (
                    empresa_id,
                    modulo_id,
                    solicitado_por_usuario_id,
                    responsavel_equipe_id,
                    status,
                    valor,
                    periodicidade,
                    data_pedido,
                    forma_pagamento_id,
                    forma_pagamento,
                    observacoes,
                    criado_em,
                    atualizado_em
                )
                VALUES (
                    :empresa_id,
                    :modulo_id,
                    :usuario_id,
                    :equipe_id,
                    'SOLICITADO',
                    :valor,
                    :periodicidade,
                    NOW(),
                    :forma_pagamento_id,
                    :forma_pagamento,
                    :observacoes,
                    NOW(),
                    NOW()
                )
                RETURNING id
            """),
            {
                "empresa_id": empresa_id,
                "modulo_id": payload.modulo_id,
                "usuario_id": member.usuario_id,
                "equipe_id": member.equipe_id,
                "valor": payload.valor,
                "periodicidade": periodicidade,
                "forma_pagamento_id": forma_pagamento_id,
                "forma_pagamento": forma_pagamento,
                "observacoes": (
                    payload.observacoes.strip()
                    if payload.observacoes
                    else None
                ),
            },
        ).scalar_one()

        _audit_admin(
            db,
            member=member,
            empresa_id=empresa_id,
            acao="PEDIDO_MODULO_CRIADO",
            recurso="pedidos_modulos_saas",
            recurso_id=pedido_id,
            detalhes={
                "modulo_id": payload.modulo_id,
                "modulo": modulo["nome"],
                "valor": payload.valor,
                "periodicidade": periodicidade,
                "forma_pagamento_id": forma_pagamento_id,
                "forma_pagamento": forma_pagamento,
                "status": "SOLICITADO",
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "pedido_id": pedido_id,
        "status": "SOLICITADO",
        "modulo_id": payload.modulo_id,
        "modulo": modulo["nome"],
    }


@router.post(
    "/empresas/{empresa_id}/pedidos-modulos/{pedido_id}/status"
)
def admin_alterar_status_pedido_modulo(
    empresa_id: int,
    pedido_id: int,
    payload: AdminModuleOrderStatusInput,
    member: Annotated[
        PlatformMemberContext,
        Depends(get_current_platform_member),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
):
    _require_admin_empresa(
        db,
        empresa_id,
    )

    pedido = db.execute(
        text("""
            SELECT
                pm.id,
                pm.modulo_id,
                pm.status,
                pm.valor,
                pm.periodicidade,
                pm.forma_pagamento,
                pm.forma_pagamento_id,
                m.nome AS modulo_nome
            FROM pedidos_modulos_saas pm
            JOIN modulos_saas m
              ON m.id = pm.modulo_id
            WHERE pm.id = :pedido_id
              AND pm.empresa_id = :empresa_id
        """),
        {
            "pedido_id": pedido_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="pedido de módulo não encontrado",
        )

    atual = str(pedido["status"]).upper()
    destino = payload.status.upper()

    transicoes = {
        "SOLICITADO": {
            "EM_ANALISE",
            "CANCELADO",
        },
        "EM_ANALISE": {
            "AGUARDANDO_PAGAMENTO",
            "CANCELADO",
        },
        "AGUARDANDO_PAGAMENTO": {
            "PAGO",
            "CANCELADO",
        },
        "PAGO": {
            "ATIVADO",
        },
        "ATIVADO": set(),
        "CANCELADO": set(),
    }

    permitidos = transicoes.get(atual)

    if permitidos is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"status atual não reconhecido: {atual}",
        )

    if destino not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"transição inválida: "
                f"{atual} -> {destino}"
            ),
        )

    permissao = (
        "MODULOS_CANCELAR"
        if destino == "CANCELADO"
        else (
            "FINANCEIRO_EDITAR"
            if destino == "PAGO"
            else "MODULOS_ATIVAR"
        )
    )

    if not member.has_permission(permissao):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "sem permissão para executar "
                f"esta etapa ({permissao})"
            ),
        )

    try:
        modulo_registro_id = None
        pagamento_id = None
        nota_fiscal_id = None

        # --------------------------------------------------------
        # AO APROVAR:
        # nasce a pendência financeira do pedido.
        # --------------------------------------------------------

        if destino == "AGUARDANDO_PAGAMENTO":
            pagamento_id = db.execute(
                text("""
                    SELECT id
                    FROM pagamentos_saas
                    WHERE empresa_id = :empresa_id
                      AND pedido_modulo_id = :pedido_id
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "empresa_id": empresa_id,
                    "pedido_id": pedido_id,
                },
            ).scalar()

            if pagamento_id is None:
                pagamento_id = db.execute(
                    text("""
                        INSERT INTO pagamentos_saas (
                            empresa_id,
                            assinatura_id,
                            pedido_modulo_id,
                            tipo,
                            status,
                            valor,
                            vencimento,
                            pago_em,
                            forma_pagamento_id,
                            forma_pagamento,
                            referencia_externa,
                            observacoes,
                            criado_em,
                            atualizado_em
                        )
                        VALUES (
                            :empresa_id,
                            NULL,
                            :pedido_id,
                            'MODULO_AVULSO',
                            'PENDENTE',
                            :valor,
                            NULL,
                            NULL,
                            :forma_pagamento_id,
                            :forma_pagamento,
                            NULL,
                            :observacoes,
                            NOW(),
                            NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "empresa_id": empresa_id,
                        "pedido_id": pedido_id,
                        "valor": pedido["valor"],
                        "forma_pagamento_id": pedido["forma_pagamento_id"],
                        "forma_pagamento": pedido["forma_pagamento"],
                        "observacoes": (
                            f"Pagamento do pedido de módulo "
                            f"#{pedido_id} - "
                            f"{pedido['modulo_nome']}"
                        ),
                    },
                ).scalar_one()

                _audit_admin(
                    db,
                    member=member,
                    empresa_id=empresa_id,
                    acao="PAGAMENTO_PEDIDO_CRIADO",
                    recurso="pagamentos_saas",
                    recurso_id=pagamento_id,
                    detalhes={
                        "pedido_id": pedido_id,
                        "modulo_id": pedido["modulo_id"],
                        "modulo": pedido["modulo_nome"],
                        "valor": pedido["valor"],
                        "status": "PENDENTE",
                    },
                )

        # --------------------------------------------------------
        # AO CONFIRMAR PAGAMENTO:
        # quita o financeiro e prepara uma NFS-e PENDENTE.
        # Não existe emissão fiscal externa nesta etapa.
        # --------------------------------------------------------

        if destino == "PAGO":
            pagamento = db.execute(
                text("""
                    SELECT
                        id,
                        status
                    FROM pagamentos_saas
                    WHERE empresa_id = :empresa_id
                      AND pedido_modulo_id = :pedido_id
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "empresa_id": empresa_id,
                    "pedido_id": pedido_id,
                },
            ).mappings().first()

            if pagamento is None:
                pagamento_id = db.execute(
                    text("""
                        INSERT INTO pagamentos_saas (
                            empresa_id,
                            assinatura_id,
                            pedido_modulo_id,
                            tipo,
                            status,
                            valor,
                            vencimento,
                            pago_em,
                            forma_pagamento_id,
                            forma_pagamento,
                            referencia_externa,
                            observacoes,
                            criado_em,
                            atualizado_em
                        )
                        VALUES (
                            :empresa_id,
                            NULL,
                            :pedido_id,
                            'MODULO_AVULSO',
                            'PAGO',
                            :valor,
                            NULL,
                            NOW(),
                            :forma_pagamento_id,
                            :forma_pagamento,
                            NULL,
                            :observacoes,
                            NOW(),
                            NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "empresa_id": empresa_id,
                        "pedido_id": pedido_id,
                        "valor": pedido["valor"],
                        "forma_pagamento_id": pedido["forma_pagamento_id"],
                        "forma_pagamento": pedido["forma_pagamento"],
                        "observacoes": (
                            f"Pagamento confirmado do pedido "
                            f"#{pedido_id} - "
                            f"{pedido['modulo_nome']}"
                        ),
                    },
                ).scalar_one()

            else:
                pagamento_id = pagamento["id"]

                db.execute(
                    text("""
                        UPDATE pagamentos_saas
                        SET
                            status = 'PAGO',
                            pago_em = COALESCE(
                                pago_em,
                                NOW()
                            ),
                            forma_pagamento_id = COALESCE(:forma_pagamento_id, forma_pagamento_id),
                            forma_pagamento = COALESCE(
                                :forma_pagamento,
                                forma_pagamento
                            ),
                            atualizado_em = NOW()
                        WHERE id = :pagamento_id
                          AND empresa_id = :empresa_id
                    """),
                    {
                        "pagamento_id": pagamento_id,
                        "empresa_id": empresa_id,
                        "forma_pagamento_id": pedido["forma_pagamento_id"],
                        "forma_pagamento": pedido["forma_pagamento"],
                    },
                )

            _audit_admin(
                db,
                member=member,
                empresa_id=empresa_id,
                acao="PAGAMENTO_PEDIDO_CONFIRMADO",
                recurso="pagamentos_saas",
                recurso_id=pagamento_id,
                detalhes={
                    "pedido_id": pedido_id,
                    "modulo_id": pedido["modulo_id"],
                    "modulo": pedido["modulo_nome"],
                    "valor": pedido["valor"],
                    "forma_pagamento_id": pedido["forma_pagamento_id"],
                    "forma_pagamento": pedido["forma_pagamento"],
                    "status": "PAGO",
                },
            )

            nota_fiscal_id = db.execute(
                text("""
                    SELECT id
                    FROM notas_fiscais_saas
                    WHERE empresa_id = :empresa_id
                      AND pagamento_id = :pagamento_id
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "empresa_id": empresa_id,
                    "pagamento_id": pagamento_id,
                },
            ).scalar()

            if nota_fiscal_id is None:
                nota_fiscal_id = db.execute(
                    text("""
                        INSERT INTO notas_fiscais_saas (
                            empresa_id,
                            assinatura_id,
                            pagamento_id,
                            tipo_documento,
                            status,
                            numero,
                            serie,
                            valor_servico,
                            valor_desconto,
                            valor_total,
                            data_emissao,
                            prestador_documento,
                            tomador_documento,
                            tomador_razao_social,
                            tomador_email,
                            codigo_servico,
                            descricao_servico,
                            referencia_externa,
                            protocolo,
                            xml_url,
                            pdf_url,
                            erro_codigo,
                            erro_mensagem,
                            criado_em,
                            atualizado_em
                        )
                        VALUES (
                            :empresa_id,
                            NULL,
                            :pagamento_id,
                            'NFSE',
                            'PENDENTE',
                            NULL,
                            NULL,
                            :valor,
                            0,
                            :valor,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            :descricao,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            NOW(),
                            NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "empresa_id": empresa_id,
                        "pagamento_id": pagamento_id,
                        "valor": pedido["valor"],
                        "descricao": (
                            f"Módulo {pedido['modulo_nome']} "
                            f"- {pedido['periodicidade'] or 'AVULSO'}"
                        ),
                    },
                ).scalar_one()

                _audit_admin(
                    db,
                    member=member,
                    empresa_id=empresa_id,
                    acao="NFSE_PREPARADA",
                    recurso="notas_fiscais_saas",
                    recurso_id=nota_fiscal_id,
                    detalhes={
                        "pedido_id": pedido_id,
                        "pagamento_id": pagamento_id,
                        "modulo_id": pedido["modulo_id"],
                        "modulo": pedido["modulo_nome"],
                        "valor": pedido["valor"],
                        "status": "PENDENTE",
                    },
                )

        # --------------------------------------------------------
        # CANCELAMENTO ANTES DO PAGAMENTO:
        # encerra também a pendência financeira.
        # --------------------------------------------------------

        if destino == "CANCELADO":
            db.execute(
                text("""
                    UPDATE pagamentos_saas
                    SET
                        status = 'CANCELADO',
                        atualizado_em = NOW()
                    WHERE empresa_id = :empresa_id
                      AND pedido_modulo_id = :pedido_id
                      AND status IN (
                          'PENDENTE',
                          'PROCESSANDO',
                          'ATRASADO'
                      )
                """),
                {
                    "empresa_id": empresa_id,
                    "pedido_id": pedido_id,
                },
            )

        if destino == "ATIVADO":
            existente = db.execute(
                text("""
                    SELECT id
                    FROM empresa_modulos_saas
                    WHERE empresa_id = :empresa_id
                      AND modulo_id = :modulo_id
                      AND status IN (
                          'ATIVO',
                          'PENDENTE'
                      )
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "empresa_id": empresa_id,
                    "modulo_id": pedido["modulo_id"],
                },
            ).scalar()

            if existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "empresa já possui este "
                        "módulo ativo"
                    ),
                )

            periodicidade = (
                str(
                    pedido["periodicidade"]
                    or "MENSAL"
                ).upper()
            )

            data_fim = None

            if periodicidade in {
                "MENSAL",
                "ANUAL",
            }:
                data_fim = _next_due_date(
                    date.today(),
                    periodicidade,
                )

            modulo_registro_id = db.execute(
                text("""
                    INSERT INTO empresa_modulos_saas (
                        empresa_id,
                        modulo_id,
                        origem,
                        status,
                        data_inicio,
                        data_fim,
                        valor,
                        periodicidade,
                        observacoes
                    )
                    VALUES (
                        :empresa_id,
                        :modulo_id,
                        'AVULSO',
                        'ATIVO',
                        CURRENT_DATE,
                        :data_fim,
                        :valor,
                        :periodicidade,
                        :observacoes
                    )
                    RETURNING id
                """),
                {
                    "empresa_id": empresa_id,
                    "modulo_id": pedido["modulo_id"],
                    "data_fim": data_fim,
                    "valor": pedido["valor"],
                    "periodicidade": periodicidade,
                    "observacoes": (
                        f"Ativado pelo pedido "
                        f"de módulo #{pedido_id}"
                    ),
                },
            ).scalar_one()

            _audit_admin(
                db,
                member=member,
                empresa_id=empresa_id,
                acao="MODULO_ATIVADO_POR_PEDIDO",
                recurso="empresa_modulos_saas",
                recurso_id=modulo_registro_id,
                detalhes={
                    "pedido_id": pedido_id,
                    "modulo_id": pedido["modulo_id"],
                    "modulo": pedido["modulo_nome"],
                    "origem": "AVULSO",
                    "valor": pedido["valor"],
                    "periodicidade": periodicidade,
                    "data_fim": data_fim,
                },
            )

        db.execute(
            text("""
                UPDATE pedidos_modulos_saas
                SET
                    status = :status,
                    data_aprovacao = CASE
                        WHEN :status = 'AGUARDANDO_PAGAMENTO'
                        THEN COALESCE(
                            data_aprovacao,
                            NOW()
                        )
                        ELSE data_aprovacao
                    END,
                    data_ativacao = CASE
                        WHEN :status = 'ATIVADO'
                        THEN COALESCE(
                            data_ativacao,
                            NOW()
                        )
                        ELSE data_ativacao
                    END,
                    atualizado_em = NOW()
                WHERE id = :pedido_id
                  AND empresa_id = :empresa_id
            """),
            {
                "status": destino,
                "pedido_id": pedido_id,
                "empresa_id": empresa_id,
            },
        )

        _audit_admin(
            db,
            member=member,
            empresa_id=empresa_id,
            acao="PEDIDO_MODULO_STATUS_ALTERADO",
            recurso="pedidos_modulos_saas",
            recurso_id=pedido_id,
            detalhes={
                "modulo_id": pedido["modulo_id"],
                "modulo": pedido["modulo_nome"],
                "status_anterior": atual,
                "status_novo": destino,
                "modulo_registro_id": modulo_registro_id,
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "pedido_id": pedido_id,
        "status_anterior": atual,
        "status": destino,
        "modulo_registro_id": modulo_registro_id,
    }


@router.get("/formas-pagamento")
def admin_list_payment_methods(
    member: Annotated[PlatformMemberContext, Depends(require_platform_permission("EMPRESAS_VER"))],
    db: Annotated[Session, Depends(get_db)],
):
    return {"items": [dict(row) for row in list_payment_methods(db)]}


@router.post("/formas-pagamento", status_code=201)
def admin_create_payment_method(
    payload: AdminPaymentMethodCreate,
    member: Annotated[PlatformMemberContext, Depends(require_platform_permission("FINANCEIRO_EDITAR"))],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        result = dict(create_payment_method(db, payload))
        _audit_admin(db, member=member, empresa_id=None, acao="FORMA_PAGAMENTO_ADMIN_CRIADA",
                     recurso="formas_pagamento", recurso_id=result["id"])
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


class AdminSubscriptionContractInput(BaseModel):
    plano_id: int = Field(gt=0)
    periodicidade: Literal["MENSAL", "ANUAL"]
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    forma_pagamento_id: int = Field(gt=0)
    renovacao_automatica: bool = False
    observacoes: str | None = None
    trial_id: int | None = Field(default=None, gt=0)


class AdminSubscriptionChargeInput(BaseModel):
    ciclo_inicio: date | None = None
    vencimento: date


@router.post("/empresas/{empresa_id}/assinaturas", status_code=201)
def admin_prepare_subscription(
    empresa_id: int,
    payload: AdminSubscriptionContractInput,
    member: Annotated[PlatformMemberContext, Depends(require_platform_permission("ASSINATURAS_EDITAR"))],
    db: Annotated[Session, Depends(get_db)],
):
    return subscriptions.prepare_contract(db, member=member, empresa_id=empresa_id, **payload.dict())


@router.post("/assinaturas/{assinatura_id}/cobrancas", status_code=201)
def admin_generate_subscription_charge(
    assinatura_id: int,
    payload: AdminSubscriptionChargeInput,
    member: Annotated[PlatformMemberContext, Depends(require_platform_permission("FINANCEIRO_EDITAR"))],
    db: Annotated[Session, Depends(get_db)],
):
    return subscriptions.generate_charge(db, member=member, assinatura_id=assinatura_id, **payload.dict())


@router.post("/pagamentos/{pagamento_id}/confirmar-assinatura")
def admin_confirm_subscription_payment(
    pagamento_id: int,
    member: Annotated[PlatformMemberContext, Depends(require_platform_permission("FINANCEIRO_EDITAR"))],
    db: Annotated[Session, Depends(get_db)],
):
    return subscriptions.confirm_payment(db, member=member, pagamento_id=pagamento_id)


# Support beta uses the existing administrative permissions and tables.
from app.admin.support import router as support_router
router.include_router(support_router)
