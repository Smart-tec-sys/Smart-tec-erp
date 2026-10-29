from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session


TIPOS_DOCUMENTO = {
    "NF_SAIDA_PRODUTO",
    "NF_SAIDA_SERVICO",
    "NF_ENTRADA_PRODUTO",
    "NF_ENTRADA_SERVICO",
    "OUTRO",
}

TIPOS_OBRIGACAO = {
    "DAS",
    "DARF",
    "FGTS",
    "INSS",
    "IMPOSTO",
    "HONORARIOS_CONTABEIS",
    "TAXA",
    "OUTRO",
}


def _empresa_id(tenant) -> int:
    empresa_id = getattr(tenant, "empresa_id", None)

    if empresa_id is None:
        empresa = getattr(tenant, "empresa", None)
        empresa_id = getattr(empresa, "id", None)

    if empresa_id is None:
        empresa_id = getattr(tenant, "id", None)

    if empresa_id is None:
        raise RuntimeError("Tenant atual sem empresa_id.")

    return int(empresa_id)


def _competencia(valor: str):
    try:
        dt = datetime.strptime(valor, "%Y-%m")
    except ValueError as exc:
        raise ValueError(
            "Competência inválida. Use o formato AAAA-MM."
        ) from exc

    return dt.date().replace(day=1)


def resumo(db: Session, tenant, competencia: str):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(competencia)

    fiscal = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN tipo_documento = 'NF_SAIDA_PRODUTO'
                        THEN valor ELSE 0
                    END
                ), 0) AS nf_produtos,

                COALESCE(SUM(
                    CASE
                        WHEN tipo_documento = 'NF_SAIDA_SERVICO'
                        THEN valor ELSE 0
                    END
                ), 0) AS nf_servicos,

                COALESCE(SUM(
                    CASE
                        WHEN tipo_documento IN (
                            'NF_SAIDA_PRODUTO',
                            'NF_SAIDA_SERVICO'
                        )
                        THEN valor ELSE 0
                    END
                ), 0) AS faturamento_fiscal,

                COUNT(*) FILTER (
                    WHERE tipo_documento = 'NF_SAIDA_PRODUTO'
                ) AS qtd_nf_produtos,

                COUNT(*) FILTER (
                    WHERE tipo_documento = 'NF_SAIDA_SERVICO'
                ) AS qtd_nf_servicos

            FROM contabilidade_documentos
            WHERE empresa_id = :empresa_id
              AND competencia = :competencia
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
        },
    ).mappings().one()

    obrigacoes = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(valor), 0) AS total_obrigacoes,

                COALESCE(SUM(
                    CASE
                        WHEN status <> 'PAGO'
                         AND status <> 'CANCELADO'
                        THEN valor ELSE 0
                    END
                ), 0) AS total_pendente,

                COALESCE(SUM(
                    CASE
                        WHEN status = 'PAGO'
                        THEN valor ELSE 0
                    END
                ), 0) AS total_pago,

                COALESCE(SUM(
                    CASE
                        WHEN tipo_obrigacao = 'HONORARIOS_CONTABEIS'
                        THEN valor ELSE 0
                    END
                ), 0) AS honorarios_contabeis

            FROM contabilidade_obrigacoes
            WHERE empresa_id = :empresa_id
              AND competencia = :competencia
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
        },
    ).mappings().one()

    fechamento = db.execute(
        text(
            """
            SELECT
                id,
                status,
                observacao,
                fechado_em
            FROM contabilidade_fechamentos
            WHERE empresa_id = :empresa_id
              AND competencia = :competencia
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
        },
    ).mappings().first()

    return {
        "competencia": competencia,
        "nf_produtos": fiscal["nf_produtos"],
        "nf_servicos": fiscal["nf_servicos"],
        "faturamento_fiscal": fiscal["faturamento_fiscal"],
        "qtd_nf_produtos": fiscal["qtd_nf_produtos"],
        "qtd_nf_servicos": fiscal["qtd_nf_servicos"],
        "total_obrigacoes": obrigacoes["total_obrigacoes"],
        "total_pendente": obrigacoes["total_pendente"],
        "total_pago": obrigacoes["total_pago"],
        "honorarios_contabeis": obrigacoes["honorarios_contabeis"],
        "fechamento": dict(fechamento) if fechamento else {
            "status": "ABERTO",
            "observacao": None,
            "fechado_em": None,
        },
    }


def listar_documentos(
    db: Session,
    tenant,
    competencia: str,
):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(competencia)

    rows = db.execute(
        text(
            """
            SELECT *
            FROM contabilidade_documentos
            WHERE empresa_id = :empresa_id
              AND competencia = :competencia
            ORDER BY data_emissao DESC, id DESC
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def criar_documento(
    db: Session,
    tenant,
    data,
):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(data.competencia)

    tipo = data.tipo_documento.strip().upper()

    if tipo not in TIPOS_DOCUMENTO:
        raise ValueError(
            "Tipo de documento fiscal inválido."
        )

    if Decimal(str(data.valor)) < 0:
        raise ValueError(
            "Valor do documento não pode ser negativo."
        )

    row = db.execute(
        text(
            """
            INSERT INTO contabilidade_documentos (
                empresa_id,
                competencia,
                tipo_documento,
                numero,
                chave_acesso,
                data_emissao,
                valor,
                pedido_id,
                compra_id,
                observacao
            )
            VALUES (
                :empresa_id,
                :competencia,
                :tipo_documento,
                :numero,
                :chave_acesso,
                :data_emissao,
                :valor,
                :pedido_id,
                :compra_id,
                :observacao
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
            "tipo_documento": tipo,
            "numero": data.numero,
            "chave_acesso": data.chave_acesso,
            "data_emissao": data.data_emissao,
            "valor": data.valor,
            "pedido_id": data.pedido_id,
            "compra_id": data.compra_id,
            "observacao": data.observacao,
        },
    ).mappings().one()

    db.commit()

    return dict(row)


def listar_obrigacoes(
    db: Session,
    tenant,
    competencia: str,
):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(competencia)

    rows = db.execute(
        text(
            """
            SELECT *
            FROM contabilidade_obrigacoes
            WHERE empresa_id = :empresa_id
              AND competencia = :competencia
            ORDER BY vencimento, id
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def criar_obrigacao(
    db: Session,
    tenant,
    data,
):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(data.competencia)

    tipo = data.tipo_obrigacao.strip().upper()

    if tipo not in TIPOS_OBRIGACAO:
        raise ValueError(
            "Tipo de obrigação contábil inválido."
        )

    if Decimal(str(data.valor)) < 0:
        raise ValueError(
            "Valor da obrigação não pode ser negativo."
        )

    row = db.execute(
        text(
            """
            INSERT INTO contabilidade_obrigacoes (
                empresa_id,
                competencia,
                tipo_obrigacao,
                descricao,
                valor,
                vencimento,
                status,
                fornecedor_id,
                observacao
            )
            VALUES (
                :empresa_id,
                :competencia,
                :tipo_obrigacao,
                :descricao,
                :valor,
                :vencimento,
                'RECEBIDO',
                :fornecedor_id,
                :observacao
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
            "tipo_obrigacao": tipo,
            "descricao": data.descricao.strip(),
            "valor": data.valor,
            "vencimento": data.vencimento,
            "fornecedor_id": data.fornecedor_id,
            "observacao": data.observacao,
        },
    ).mappings().one()

    db.commit()

    return dict(row)


def gerar_conta_pagar(
    db: Session,
    tenant,
    obrigacao_id: int,
):
    empresa_id = _empresa_id(tenant)

    obrigacao = db.execute(
        text(
            """
            SELECT *
            FROM contabilidade_obrigacoes
            WHERE id = :id
              AND empresa_id = :empresa_id
            FOR UPDATE
            """
        ),
        {
            "id": obrigacao_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if obrigacao is None:
        raise ValueError(
            "Obrigação contábil não encontrada."
        )

    if obrigacao["financeiro_id"] is not None:
        raise ValueError(
            "Esta obrigação já possui conta a pagar vinculada."
        )

    if obrigacao["status"] in {
        "PAGO",
        "CANCELADO",
    }:
        raise ValueError(
            "Obrigação paga ou cancelada não pode gerar nova conta."
        )

    financeiro = db.execute(
        text(
            """
            INSERT INTO financeiro (
                tipo,
                descricao,
                valor,
                vencimento,
                pagamento,
                status,
                fornecedor_id,
                categoria,
                observacao,
                empresa_id
            )
            VALUES (
                'P',
                :descricao,
                :valor,
                :vencimento,
                NULL,
                'ABERTO',
                :fornecedor_id,
                'CONTABILIDADE',
                :observacao,
                :empresa_id
            )
            RETURNING *
            """
        ),
        {
            "descricao": obrigacao["descricao"],
            "valor": obrigacao["valor"],
            "vencimento": obrigacao["vencimento"],
            "fornecedor_id": obrigacao["fornecedor_id"],
            "observacao": obrigacao["observacao"],
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    atualizada = db.execute(
        text(
            """
            UPDATE contabilidade_obrigacoes
            SET
                financeiro_id = :financeiro_id,
                status = 'AGUARDANDO_PAGAMENTO',
                atualizado_em = now()
            WHERE id = :id
              AND empresa_id = :empresa_id
            RETURNING *
            """
        ),
        {
            "financeiro_id": financeiro["id"],
            "id": obrigacao_id,
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    db.commit()

    return {
        "obrigacao": dict(atualizada),
        "financeiro": dict(financeiro),
    }


def marcar_paga(
    db: Session,
    tenant,
    obrigacao_id: int,
    pagamento,
):
    empresa_id = _empresa_id(tenant)

    obrigacao = db.execute(
        text(
            """
            SELECT *
            FROM contabilidade_obrigacoes
            WHERE id = :id
              AND empresa_id = :empresa_id
            FOR UPDATE
            """
        ),
        {
            "id": obrigacao_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if obrigacao is None:
        raise ValueError(
            "Obrigação contábil não encontrada."
        )

    if obrigacao["status"] == "CANCELADO":
        raise ValueError(
            "Obrigação cancelada não pode ser marcada como paga."
        )

    if obrigacao["financeiro_id"] is None:
        raise ValueError(
            "A obrigação precisa gerar uma Conta a Pagar antes de ser marcada como paga."
        )

    if obrigacao["financeiro_id"] is not None:
        db.execute(
            text(
                """
                UPDATE financeiro
                SET
                    status = 'PAGO',
                    pagamento = :pagamento
                WHERE id = :financeiro_id
                  AND empresa_id = :empresa_id
                """
            ),
            {
                "pagamento": pagamento,
                "financeiro_id": obrigacao["financeiro_id"],
                "empresa_id": empresa_id,
            },
        )

    atualizada = db.execute(
        text(
            """
            UPDATE contabilidade_obrigacoes
            SET
                status = 'PAGO',
                atualizado_em = now()
            WHERE id = :id
              AND empresa_id = :empresa_id
            RETURNING *
            """
        ),
        {
            "id": obrigacao_id,
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    db.commit()

    return dict(atualizada)


def fechar_competencia(
    db: Session,
    tenant,
    competencia: str,
    observacao=None,
):
    empresa_id = _empresa_id(tenant)
    comp = _competencia(competencia)

    row = db.execute(
        text(
            """
            INSERT INTO contabilidade_fechamentos (
                empresa_id,
                competencia,
                status,
                observacao,
                fechado_em
            )
            VALUES (
                :empresa_id,
                :competencia,
                'FECHADO',
                :observacao,
                now()
            )
            ON CONFLICT (
                empresa_id,
                competencia
            )
            DO UPDATE SET
                status = 'FECHADO',
                observacao = EXCLUDED.observacao,
                fechado_em = now(),
                atualizado_em = now()
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "competencia": comp,
            "observacao": observacao,
        },
    ).mappings().one()

    db.commit()

    return dict(row)