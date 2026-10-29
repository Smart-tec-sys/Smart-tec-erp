from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.orm import Session


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
            "Competência inválida. Use AAAA-MM."
        ) from exc

    return dt.date().replace(day=1)


def _money(valor):
    return Decimal(str(valor or 0)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _percent(valor):
    return Decimal(str(valor or 0)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def listar_parceiros(
    db: Session,
    tenant,
    somente_ativos: bool = False,
):
    empresa_id = _empresa_id(tenant)

    sql = """
        SELECT *
        FROM parceiros_comerciais
        WHERE empresa_id = :empresa_id
    """

    if somente_ativos:
        sql += " AND ativo = TRUE "

    sql += " ORDER BY nome, id "

    rows = db.execute(
        text(sql),
        {
            "empresa_id": empresa_id,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def criar_parceiro(
    db: Session,
    tenant,
    data,
):
    empresa_id = _empresa_id(tenant)

    nome = data.nome.strip()

    if not nome:
        raise ValueError(
            "Informe o nome do parceiro."
        )

    percentual = _percent(
        data.percentual_padrao
    )

    if percentual < 0 or percentual > 100:
        raise ValueError(
            "Percentual padrão do parceiro deve ficar entre 0 e 100."
        )

    row = db.execute(
        text(
            """
            INSERT INTO parceiros_comerciais (
                empresa_id,
                nome,
                documento,
                email,
                telefone,
                percentual_padrao,
                observacao
            )
            VALUES (
                :empresa_id,
                :nome,
                :documento,
                :email,
                :telefone,
                :percentual_padrao,
                :observacao
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "nome": nome,
            "documento": data.documento,
            "email": data.email,
            "telefone": data.telefone,
            "percentual_padrao": percentual,
            "observacao": data.observacao,
        },
    ).mappings().one()

    db.commit()

    return dict(row)


def listar_representantes(
    db: Session,
    tenant,
    somente_ativos: bool = False,
):
    empresa_id = _empresa_id(tenant)

    sql = """
        SELECT
            r.*,
            p.nome AS parceiro_nome
        FROM representantes r
        LEFT JOIN parceiros_comerciais p
               ON p.id = r.parceiro_id
              AND p.empresa_id = r.empresa_id
        WHERE r.empresa_id = :empresa_id
    """

    if somente_ativos:
        sql += " AND r.ativo = TRUE "

    sql += " ORDER BY r.nome, r.id "

    rows = db.execute(
        text(sql),
        {
            "empresa_id": empresa_id,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def criar_representante(
    db: Session,
    tenant,
    data,
):
    empresa_id = _empresa_id(tenant)

    nome = data.nome.strip()

    if not nome:
        raise ValueError(
            "Informe o nome do representante."
        )

    tipo = str(
        data.tipo_rt_padrao or "PERCENTUAL"
    ).strip().upper()

    if tipo not in {
        "PERCENTUAL",
        "VALOR_FIXO",
    }:
        raise ValueError(
            "Tipo de RT deve ser PERCENTUAL ou VALOR_FIXO."
        )

    percentual = _percent(
        data.percentual_rt_padrao
    )

    valor_fixo = _money(
        data.valor_rt_padrao
    )

    if percentual < 0 or percentual > 100:
        raise ValueError(
            "Percentual de RT deve ficar entre 0 e 100."
        )

    if valor_fixo < 0:
        raise ValueError(
            "Valor fixo de RT não pode ser negativo."
        )

    parceiro_id = data.parceiro_id

    if parceiro_id is not None:
        parceiro = db.execute(
            text(
                """
                SELECT id
                FROM parceiros_comerciais
                WHERE id = :id
                  AND empresa_id = :empresa_id
                """
            ),
            {
                "id": parceiro_id,
                "empresa_id": empresa_id,
            },
        ).first()

        if parceiro is None:
            raise ValueError(
                "Parceiro não encontrado para a empresa atual."
            )

    row = db.execute(
        text(
            """
            INSERT INTO representantes (
                empresa_id,
                parceiro_id,
                nome,
                documento,
                email,
                telefone,
                tipo_rt_padrao,
                percentual_rt_padrao,
                valor_rt_padrao,
                observacao
            )
            VALUES (
                :empresa_id,
                :parceiro_id,
                :nome,
                :documento,
                :email,
                :telefone,
                :tipo_rt_padrao,
                :percentual_rt_padrao,
                :valor_rt_padrao,
                :observacao
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "parceiro_id": parceiro_id,
            "nome": nome,
            "documento": data.documento,
            "email": data.email,
            "telefone": data.telefone,
            "tipo_rt_padrao": tipo,
            "percentual_rt_padrao": percentual,
            "valor_rt_padrao": valor_fixo,
            "observacao": data.observacao,
        },
    ).mappings().one()

    db.commit()

    return dict(row)


def listar_rt(
    db: Session,
    tenant,
    competencia: str | None = None,
    status: str | None = None,
):
    empresa_id = _empresa_id(tenant)

    filtros = [
        "rt.empresa_id = :empresa_id"
    ]

    params = {
        "empresa_id": empresa_id,
    }

    if competencia:
        filtros.append(
            "rt.competencia = :competencia"
        )
        params["competencia"] = _competencia(
            competencia
        )

    if status:
        filtros.append(
            "rt.status = :status"
        )
        params["status"] = status.strip().upper()

    where = " AND ".join(filtros)

    rows = db.execute(
        text(
            f"""
            SELECT
                rt.*,
                r.nome AS representante_nome,
                p.nome AS parceiro_nome,
                ped.numero AS venda_numero,
                ped.total_final AS venda_total
            FROM representantes_rt rt
            JOIN representantes r
              ON r.id = rt.representante_id
            JOIN pedidos ped
              ON ped.id = rt.pedido_id
            LEFT JOIN parceiros_comerciais p
              ON p.id = rt.parceiro_id
            WHERE {where}
            ORDER BY
                rt.competencia DESC,
                rt.id DESC
            """
        ),
        params,
    ).mappings().all()

    return [dict(row) for row in rows]


def criar_rt(
    db: Session,
    tenant,
    data,
):
    empresa_id = _empresa_id(tenant)
    competencia = _competencia(
        data.competencia
    )

    pedido = db.execute(
        text(
            """
            SELECT
                id,
                numero,
                total_final
            FROM pedidos
            WHERE id = :pedido_id
              AND empresa_id = :empresa_id
            """
        ),
        {
            "pedido_id": data.pedido_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if pedido is None:
        raise ValueError(
            "Venda não encontrada para a empresa atual."
        )

    representante = db.execute(
        text(
            """
            SELECT *
            FROM representantes
            WHERE id = :representante_id
              AND empresa_id = :empresa_id
              AND ativo = TRUE
            """
        ),
        {
            "representante_id": data.representante_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if representante is None:
        raise ValueError(
            "Representante ativo não encontrado."
        )

    tipo = (
        str(data.tipo_calculo).strip().upper()
        if data.tipo_calculo
        else str(
            representante["tipo_rt_padrao"]
        ).strip().upper()
    )

    if tipo not in {
        "PERCENTUAL",
        "VALOR_FIXO",
    }:
        raise ValueError(
            "Tipo de RT inválido."
        )

    base = _money(
        pedido["total_final"]
    )

    percentual = (
        _percent(data.percentual)
        if data.percentual is not None
        else _percent(
            representante["percentual_rt_padrao"]
        )
    )

    valor_fixo = (
        _money(data.valor_fixo)
        if data.valor_fixo is not None
        else _money(
            representante["valor_rt_padrao"]
        )
    )

    if percentual < 0 or percentual > 100:
        raise ValueError(
            "Percentual de RT deve ficar entre 0 e 100."
        )

    if valor_fixo < 0:
        raise ValueError(
            "Valor fixo de RT não pode ser negativo."
        )

    if tipo == "PERCENTUAL":
        valor_rt = _money(
            base * percentual / Decimal("100")
        )
    else:
        valor_rt = valor_fixo

    if valor_rt <= 0:
        raise ValueError(
            "O RT calculado deve ser maior que zero."
        )

    parceiro_id = representante["parceiro_id"]

    try:
        row = db.execute(
            text(
                """
                INSERT INTO representantes_rt (
                    empresa_id,
                    pedido_id,
                    representante_id,
                    parceiro_id,
                    competencia,
                    vencimento,
                    base_calculo,
                    tipo_calculo,
                    percentual,
                    valor_fixo,
                    valor_rt,
                    status,
                    observacao
                )
                VALUES (
                    :empresa_id,
                    :pedido_id,
                    :representante_id,
                    :parceiro_id,
                    :competencia,
                    :vencimento,
                    :base_calculo,
                    :tipo_calculo,
                    :percentual,
                    :valor_fixo,
                    :valor_rt,
                    'PENDENTE',
                    :observacao
                )
                RETURNING *
                """
            ),
            {
                "empresa_id": empresa_id,
                "pedido_id": data.pedido_id,
                "representante_id": data.representante_id,
                "parceiro_id": parceiro_id,
                "competencia": competencia,
                "vencimento": data.vencimento,
                "base_calculo": base,
                "tipo_calculo": tipo,
                "percentual": percentual,
                "valor_fixo": valor_fixo,
                "valor_rt": valor_rt,
                "observacao": data.observacao,
            },
        ).mappings().one()

        db.commit()

        return dict(row)

    except Exception as exc:
        db.rollback()

        if "uq_representante_rt_venda_ativa" in str(exc):
            raise ValueError(
                "Já existe RT ativo deste representante para esta venda."
            ) from exc

        raise


def gerar_conta_pagar(
    db: Session,
    tenant,
    rt_id: int,
):
    empresa_id = _empresa_id(tenant)

    rt = db.execute(
        text(
            """
            SELECT
                rt.*,
                r.nome AS representante_nome,
                ped.numero AS venda_numero
            FROM representantes_rt rt
            JOIN representantes r
              ON r.id = rt.representante_id
            JOIN pedidos ped
              ON ped.id = rt.pedido_id
            WHERE rt.id = :rt_id
              AND rt.empresa_id = :empresa_id
            FOR UPDATE OF rt
            """
        ),
        {
            "rt_id": rt_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if rt is None:
        raise ValueError(
            "RT não encontrado."
        )

    if rt["status"] == "CANCELADO":
        raise ValueError(
            "RT cancelado não pode gerar pagamento."
        )

    if rt["status"] == "PAGO":
        raise ValueError(
            "RT já está pago."
        )

    if rt["financeiro_id"] is not None:
        raise ValueError(
            "Este RT já possui Conta a Pagar vinculada."
        )

    if rt["vencimento"] is None:
        raise ValueError(
            "Informe o vencimento do RT antes de gerar a Conta a Pagar."
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
                cliente_id,
                fornecedor_id,
                pedido_id,
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
                NULL,
                NULL,
                :pedido_id,
                'RT_REPRESENTANTE',
                :observacao,
                :empresa_id
            )
            RETURNING *
            """
        ),
        {
            "descricao": (
                f"RT representante "
                f"{rt['representante_nome']} - "
                f"{rt['venda_numero']}"
            ),
            "valor": rt["valor_rt"],
            "vencimento": rt["vencimento"],
            "pedido_id": rt["pedido_id"],
            "observacao": rt["observacao"],
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    atualizada = db.execute(
        text(
            """
            UPDATE representantes_rt
            SET
                financeiro_id = :financeiro_id,
                status = 'AGUARDANDO_PAGAMENTO',
                atualizado_em = now()
            WHERE id = :rt_id
              AND empresa_id = :empresa_id
            RETURNING *
            """
        ),
        {
            "financeiro_id": financeiro["id"],
            "rt_id": rt_id,
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    db.commit()

    return {
        "rt": dict(atualizada),
        "financeiro": dict(financeiro),
    }


def marcar_pago(
    db: Session,
    tenant,
    rt_id: int,
    pagamento,
):
    empresa_id = _empresa_id(tenant)

    rt = db.execute(
        text(
            """
            SELECT *
            FROM representantes_rt
            WHERE id = :rt_id
              AND empresa_id = :empresa_id
            FOR UPDATE
            """
        ),
        {
            "rt_id": rt_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if rt is None:
        raise ValueError(
            "RT não encontrado."
        )

    if rt["status"] == "CANCELADO":
        raise ValueError(
            "RT cancelado não pode ser pago."
        )

    if rt["status"] == "PAGO":
        raise ValueError(
            "RT já está pago."
        )

    if rt["financeiro_id"] is None:
        raise ValueError(
            "Gere a Conta a Pagar do RT antes de marcar como pago."
        )

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
            "financeiro_id": rt["financeiro_id"],
            "empresa_id": empresa_id,
        },
    )

    atualizada = db.execute(
        text(
            """
            UPDATE representantes_rt
            SET
                status = 'PAGO',
                pago_em = :pagamento,
                atualizado_em = now()
            WHERE id = :rt_id
              AND empresa_id = :empresa_id
            RETURNING *
            """
        ),
        {
            "pagamento": pagamento,
            "rt_id": rt_id,
            "empresa_id": empresa_id,
        },
    ).mappings().one()

    db.commit()

    return dict(atualizada)

# ============================================================
# CARTEIRA DO PARCEIRO
# ============================================================

def _validar_parceiro_carteira(
    db: Session,
    empresa_id: int,
    parceiro_id: int,
):
    parceiro = db.execute(
        text(
            """
            SELECT
                id,
                nome
            FROM parceiros_comerciais
            WHERE id = :parceiro_id
              AND empresa_id = :empresa_id
              AND ativo = TRUE
            """
        ),
        {
            "parceiro_id": parceiro_id,
            "empresa_id": empresa_id,
        },
    ).mappings().first()

    if parceiro is None:
        raise ValueError(
            "Parceiro não encontrado ou inativo para a empresa atual."
        )

    return parceiro


def listar_representantes_parceiro(
    db: Session,
    tenant,
    parceiro_id: int,
    termo: str | None = None,
):
    empresa_id = _empresa_id(tenant)

    _validar_parceiro_carteira(
        db,
        empresa_id,
        parceiro_id,
    )

    sql = """
        SELECT
            id,
            empresa_id,
            parceiro_id,
            nome,
            documento,
            email,
            telefone,
            endereco,
            ativo,
            criado_em,
            atualizado_em
        FROM parceiro_representantes
        WHERE empresa_id = :empresa_id
          AND parceiro_id = :parceiro_id
          AND ativo = TRUE
    """

    params = {
        "empresa_id": empresa_id,
        "parceiro_id": parceiro_id,
    }

    termo_limpo = str(termo or "").strip()

    if termo_limpo:
        sql += """
          AND nome ILIKE :termo
        """

        params["termo"] = f"%{termo_limpo}%"

    sql += """
        ORDER BY nome, id
        LIMIT 50
    """

    rows = db.execute(
        text(sql),
        params,
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


def criar_representante_parceiro(
    db: Session,
    tenant,
    parceiro_id: int,
    data,
):
    empresa_id = _empresa_id(tenant)

    _validar_parceiro_carteira(
        db,
        empresa_id,
        parceiro_id,
    )

    nome = str(data.nome or "").strip()

    if not nome:
        raise ValueError(
            "Informe o representante."
        )

    # Se já existir exatamente o mesmo nome dentro do mesmo
    # parceiro, reaproveita o registro em vez de duplicar.
    existente = db.execute(
        text(
            """
            SELECT *
            FROM parceiro_representantes
            WHERE empresa_id = :empresa_id
              AND parceiro_id = :parceiro_id
              AND LOWER(TRIM(nome)) = LOWER(TRIM(:nome))
              AND ativo = TRUE
            ORDER BY id
            LIMIT 1
            """
        ),
        {
            "empresa_id": empresa_id,
            "parceiro_id": parceiro_id,
            "nome": nome,
        },
    ).mappings().first()

    if existente is not None:
        return dict(existente)

    row = db.execute(
        text(
            """
            INSERT INTO parceiro_representantes (
                empresa_id,
                parceiro_id,
                nome,
                documento,
                email,
                telefone,
                endereco
            )
            VALUES (
                :empresa_id,
                :parceiro_id,
                :nome,
                :documento,
                :email,
                :telefone,
                :endereco
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "parceiro_id": parceiro_id,
            "nome": nome,
            "documento": data.documento,
            "email": data.email,
            "telefone": data.telefone,
            "endereco": data.endereco,
        },
    ).mappings().one()

    db.commit()

    return dict(row)


def listar_clientes_parceiro(
    db: Session,
    tenant,
    parceiro_id: int,
    termo: str | None = None,
):
    empresa_id = _empresa_id(tenant)

    _validar_parceiro_carteira(
        db,
        empresa_id,
        parceiro_id,
    )

    sql = """
        SELECT
            c.id,
            c.empresa_id,
            c.parceiro_id,
            c.representante_parceiro_id,
            c.nome,
            c.documento,
            c.email,
            c.telefone,
            c.endereco,
            c.cadastro_completo,
            c.ativo,
            c.criado_em,
            c.atualizado_em,
            r.nome AS representante_nome
        FROM parceiro_clientes c
        LEFT JOIN parceiro_representantes r
               ON r.id = c.representante_parceiro_id
              AND r.empresa_id = c.empresa_id
              AND r.parceiro_id = c.parceiro_id
        WHERE c.empresa_id = :empresa_id
          AND c.parceiro_id = :parceiro_id
          AND c.ativo = TRUE
    """

    params = {
        "empresa_id": empresa_id,
        "parceiro_id": parceiro_id,
    }

    termo_limpo = str(termo or "").strip()

    if termo_limpo:
        sql += """
          AND c.nome ILIKE :termo
        """

        params["termo"] = f"%{termo_limpo}%"

    sql += """
        ORDER BY c.nome, c.id
        LIMIT 50
    """

    rows = db.execute(
        text(sql),
        params,
    ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


def criar_cliente_parceiro(
    db: Session,
    tenant,
    parceiro_id: int,
    data,
):
    empresa_id = _empresa_id(tenant)

    _validar_parceiro_carteira(
        db,
        empresa_id,
        parceiro_id,
    )

    nome = str(data.nome or "").strip()

    if not nome:
        raise ValueError(
            "Informe o cliente."
        )

    representante_id = (
        int(data.representante_parceiro_id)
        if data.representante_parceiro_id is not None
        else None
    )

    if representante_id is not None:
        representante = db.execute(
            text(
                """
                SELECT id
                FROM parceiro_representantes
                WHERE id = :representante_id
                  AND empresa_id = :empresa_id
                  AND parceiro_id = :parceiro_id
                  AND ativo = TRUE
                """
            ),
            {
                "representante_id": representante_id,
                "empresa_id": empresa_id,
                "parceiro_id": parceiro_id,
            },
        ).first()

        if representante is None:
            raise ValueError(
                "Representante não pertence ao parceiro selecionado."
            )

    row = db.execute(
        text(
            """
            INSERT INTO parceiro_clientes (
                empresa_id,
                parceiro_id,
                representante_parceiro_id,
                nome,
                documento,
                email,
                telefone,
                endereco,
                cadastro_completo
            )
            VALUES (
                :empresa_id,
                :parceiro_id,
                :representante_parceiro_id,
                :nome,
                :documento,
                :email,
                :telefone,
                :endereco,
                :cadastro_completo
            )
            RETURNING *
            """
        ),
        {
            "empresa_id": empresa_id,
            "parceiro_id": parceiro_id,
            "representante_parceiro_id": representante_id,
            "nome": nome,
            "documento": data.documento,
            "email": data.email,
            "telefone": data.telefone,
            "endereco": data.endereco,
            "cadastro_completo": bool(
                data.cadastro_completo
            ),
        },
    ).mappings().one()

    db.commit()

    return dict(row)