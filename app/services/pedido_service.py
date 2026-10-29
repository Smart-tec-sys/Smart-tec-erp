from datetime import date
from app.services.origem_comercial import CLIENTE_FINAL_CAMPOS, validar_origem_comercial
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models.orcamento import OrcamentoDB
from app.models.financeiro import FinanceiroDB
from app.models.pedido import PedidoDB, PedidoItemDB


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


def _decimal(valor, padrao="0.00"):
    if valor is None:
        return Decimal(padrao)

    return Decimal(str(valor))


def _item_dict(item: PedidoItemDB) -> dict:
    return {
        "id": item.id,
        "tipo_item": item.tipo_item or "PRODUTO",
        "produto_id": item.produto_id,
        "descricao": item.descricao,
        "codigo_interno": item.codigo_interno,
        "grupo_tecnico": item.grupo_tecnico,
        "modelo_tecnico": item.modelo_tecnico,
        "unidade": item.unidade,
        "quantidade": _decimal(item.quantidade, "0.0000"),
        "largura": _decimal(item.largura, "0.000"),
        "altura": _decimal(item.altura, "0.000"),
        "area": _decimal(item.area, "0.0000"),
        "preco_unitario": _decimal(item.preco_unitario, "0.0000"),
        "desconto": _decimal(item.desconto),
        "subtotal": _decimal(item.subtotal),
        "observacao_item": item.observacao_item,
        "material": item.material,
        "cor": item.cor,
        "acionamento": item.acionamento,
        "lado_comando": item.lado_comando,
        "calculo_producao_status": item.calculo_producao_status,
        "dados_tecnicos": item.dados_tecnicos,
    }


def _pedido_dict(pedido: PedidoDB) -> dict:
    return {
        "id": pedido.id,
        "numero": pedido.numero,
        "empresa_id": pedido.empresa_id,
        "cliente_id": pedido.cliente_id,
        "cliente_final_nome": pedido.cliente_final_nome,
        "cliente_final_documento": pedido.cliente_final_documento,
        "cliente_final_telefone": pedido.cliente_final_telefone,
        "cliente_final_email": pedido.cliente_final_email,
        "cliente_final_endereco": pedido.cliente_final_endereco,

        "orcamento_id": pedido.orcamento_id,
        "vendedor_id": pedido.vendedor_id,
        "parceiro_id": pedido.parceiro_id,
        "representante_id": pedido.representante_id,
        "orcamento_numero": (
            pedido.orcamento.numero
            if pedido.orcamento is not None
            else None
        ),
        "status": pedido.status,
        "perfil_comercial": pedido.perfil_comercial or "VAREJO",
        "data_venda": pedido.data_venda,
        "prazo_entrega": pedido.prazo_entrega,
        "canal_venda": pedido.canal_venda,
        "total": _decimal(pedido.total),
        "desconto": _decimal(pedido.desconto),
        "total_final": _decimal(pedido.total_final),
        "percentual_parceiro": pedido.percentual_parceiro,
        "incluir_rt": pedido.incluir_rt,
        "tipo_rt": pedido.tipo_rt,
        "percentual_rt": pedido.percentual_rt,
        "valor_rt": pedido.valor_rt,
        "incluir_taxa_bancaria": pedido.incluir_taxa_bancaria,
        "taxa_bancaria_percentual": pedido.taxa_bancaria_percentual,
        "valor_parceiro": pedido.valor_parceiro,
        "valor_taxa_bancaria": pedido.valor_taxa_bancaria,
        "total_cliente_final": pedido.total_cliente_final,
        "observacao": pedido.observacao,
        "observacao_interna": pedido.observacao_interna,
        "criado_em": pedido.criado_em,
        "atualizado_em": pedido.atualizado_em,
        "itens": [
            _item_dict(item)
            for item in pedido.itens
        ],
    }


def listar(db: Session, tenant):
    empresa_id = _empresa_id(tenant)

    pedidos = (
        db.query(PedidoDB)
        .options(
            selectinload(PedidoDB.itens),
            selectinload(PedidoDB.orcamento),
        )
        .filter(
            PedidoDB.empresa_id == empresa_id
        )
        .order_by(
            PedidoDB.id.desc()
        )
        .all()
    )

    return [
        _pedido_dict(pedido)
        for pedido in pedidos
    ]


def obter(
    db: Session,
    pedido_id: int,
    tenant,
):
    empresa_id = _empresa_id(tenant)

    pedido = (
        db.query(PedidoDB)
        .options(
            selectinload(PedidoDB.itens),
            selectinload(PedidoDB.orcamento),
        )
        .filter(
            PedidoDB.id == pedido_id,
            PedidoDB.empresa_id == empresa_id,
        )
        .first()
    )

    if pedido is None:
        return None

    return _pedido_dict(pedido)


def converter_orcamento(
    db: Session,
    orcamento_id: int,
    tenant,
    prazo_entrega=None,
    canal_venda=None,
):
    empresa_id = _empresa_id(tenant)

    orcamento = (
        db.query(OrcamentoDB)
        .options(
            selectinload(OrcamentoDB.itens)
        )
        .filter(
            OrcamentoDB.id == orcamento_id,
            OrcamentoDB.empresa_id == empresa_id,
        )
        .first()
    )

    if orcamento is None:
        raise ValueError(
            "Orçamento não encontrado para a empresa atual."
        )

    status_orcamento = str(
        orcamento.status or ""
    ).strip().upper()

    if status_orcamento != "APROVADO":
        raise ValueError(
            "O orçamento precisa estar salvo com status APROVADO antes de ser convertido em venda."
        )

    existente = (
        db.query(PedidoDB)
        .filter(
            PedidoDB.empresa_id == empresa_id,
            PedidoDB.orcamento_id == orcamento_id,
        )
        .first()
    )

    if existente is not None:
        referencia = existente.numero or existente.id

        raise ValueError(
            f"O orçamento já foi convertido "
            f"na venda/pedido {referencia}."
        )

    if not orcamento.itens:
        raise ValueError(
            "O orçamento não possui itens para converter."
        )

    validar_origem_comercial(
        orcamento.cliente_id, orcamento.parceiro_id,
        {key: getattr(orcamento, key) for key in CLIENTE_FINAL_CAMPOS},
    )

    pedido = PedidoDB(
        empresa_id=empresa_id,
        numero=None,
        cliente_id=orcamento.cliente_id,
        cliente_final_nome=orcamento.cliente_final_nome,
        cliente_final_documento=orcamento.cliente_final_documento,
        cliente_final_telefone=orcamento.cliente_final_telefone,
        cliente_final_email=orcamento.cliente_final_email,
        cliente_final_endereco=orcamento.cliente_final_endereco,

        orcamento_id=orcamento.id,
        vendedor_id=orcamento.vendedor_id,
        parceiro_id=orcamento.parceiro_id,
        representante_id=orcamento.representante_id,
        status="ABERTO",
        perfil_comercial=(
            orcamento.perfil_comercial or "VAREJO"
        ),
        data_venda=date.today(),
        prazo_entrega=prazo_entrega,
        canal_venda=(
            (canal_venda or "").strip()
            or None
        ),
        total=orcamento.total or 0,
        desconto=orcamento.desconto or 0,
        total_final=orcamento.total_final or 0,
        percentual_parceiro=orcamento.percentual_parceiro,
        incluir_rt=orcamento.incluir_rt,
        tipo_rt=orcamento.tipo_rt,
        percentual_rt=orcamento.percentual_rt,
        valor_rt=orcamento.valor_rt,
        incluir_taxa_bancaria=orcamento.incluir_taxa_bancaria,
        taxa_bancaria_percentual=orcamento.taxa_bancaria_percentual,
        valor_parceiro=orcamento.valor_parceiro,
        valor_taxa_bancaria=orcamento.valor_taxa_bancaria,
        total_cliente_final=orcamento.total_cliente_final,
        observacao=orcamento.observacao,
        observacao_interna=orcamento.observacao_interna,
    )

    db.add(pedido)
    db.flush()

    pedido.numero = f"VEN-{pedido.id:06d}"

    for origem in orcamento.itens:
        item = PedidoItemDB(
            pedido_id=pedido.id,
            tipo_item=origem.tipo_item or "PRODUTO",
            produto_id=origem.produto_id,
            descricao=origem.descricao,
            codigo_interno=origem.codigo_interno,
            grupo_tecnico=origem.grupo_tecnico,
            modelo_tecnico=origem.modelo_tecnico,
            unidade=origem.unidade,
            quantidade=origem.quantidade,
            largura=origem.largura or 0,
            altura=origem.altura or 0,
            area=origem.area or 0,
            preco_unitario=origem.preco_unitario,
            desconto=origem.desconto or 0,
            subtotal=origem.subtotal or 0,
            observacao_item=origem.observacao_item,
            material=origem.material,
            cor=origem.cor,
            acionamento=origem.acionamento,
            lado_comando=origem.lado_comando,
            calculo_producao_status=(
                origem.calculo_producao_status
            ),
            dados_tecnicos=origem.dados_tecnicos,
        )

        db.add(item)

    db.commit()

    pedido = (
        db.query(PedidoDB)
        .options(
            selectinload(PedidoDB.itens),
            selectinload(PedidoDB.orcamento),
        )
        .filter(
            PedidoDB.id == pedido.id,
            PedidoDB.empresa_id == empresa_id,
        )
        .first()
    )

    return _pedido_dict(pedido)

def gerar_conta_receber(
    db: Session,
    pedido_id: int,
    tenant,
    vencimento,
    categoria="VENDAS",
    observacao=None,
):
    empresa_id = _empresa_id(tenant)

    pedido = (
        db.query(PedidoDB)
        .filter(
            PedidoDB.id == pedido_id,
            PedidoDB.empresa_id == empresa_id,
        )
        .first()
    )

    if pedido is None:
        raise ValueError(
            "Venda/pedido não encontrado para a empresa atual."
        )

    existente = (
        db.query(FinanceiroDB)
        .filter(
            FinanceiroDB.empresa_id == empresa_id,
            FinanceiroDB.pedido_id == pedido_id,
            FinanceiroDB.tipo == "R",
        )
        .first()
    )

    if existente is not None:
        raise ValueError(
            f"A venda {pedido.numero or pedido.id} já possui conta a receber vinculada."
        )

    valor = _decimal(pedido.total_final)

    if valor <= 0:
        raise ValueError(
            "A venda não possui valor final positivo para gerar conta a receber."
        )

    titulo = FinanceiroDB(
        empresa_id=empresa_id,
        tipo="R",
        descricao=f"Venda {pedido.numero or pedido.id}",
        valor=valor,
        vencimento=vencimento,
        pagamento=None,
        status="ABERTO",
        cliente_id=pedido.cliente_id,
        fornecedor_id=None,
        pedido_id=pedido.id,
        categoria=(categoria or "VENDAS").strip() or "VENDAS",
        observacao=(observacao or "").strip() or None,
    )

    db.add(titulo)
    db.commit()
    db.refresh(titulo)

    return {
        "id": titulo.id,
        "pedido_id": pedido.id,
        "cliente_id": titulo.cliente_id,
        "descricao": titulo.descricao,
        "valor": _decimal(titulo.valor),
        "vencimento": titulo.vencimento,
        "status": titulo.status or "ABERTO",
        "categoria": titulo.categoria,
        "observacao": titulo.observacao,
    }

def _pedido_para_alteracao(db, pedido_id, tenant):
    return (db.query(PedidoDB)
            .filter(PedidoDB.id == pedido_id, PedidoDB.empresa_id == _empresa_id(tenant))
            .with_for_update().first())


def atualizar(db, pedido_id, tenant, data):
    from sqlalchemy import text
    pedido = _pedido_para_alteracao(db, pedido_id, tenant)
    if pedido is None:
        return None
    changes = data.dict(exclude_unset=True)
    rt_fields = {"representante_id", "incluir_rt", "tipo_rt", "percentual_rt", "valor_rt"}
    if rt_fields.intersection(changes):
        _validar_rt_representante(
            changes.get("representante_id", pedido.representante_id),
            changes.get("incluir_rt", getattr(pedido, "incluir_rt", None)),
            changes.get("percentual_rt", getattr(pedido, "percentual_rt", None)),
            changes.get("valor_rt", getattr(pedido, "valor_rt", None)),
        )
    cliente_final = {key: changes.get(key, getattr(pedido, key, None)) for key in CLIENTE_FINAL_CAMPOS}
    validar_origem_comercial(
        changes.get("cliente_id", pedido.cliente_id),
        changes.get("parceiro_id", pedido.parceiro_id), cliente_final,
    )
    tables = {"cliente_id": "clientes", "vendedor_id": "funcionarios",
              "parceiro_id": "parceiros_comerciais", "representante_id": "representantes"}
    for field, table in tables.items():
        if changes.get(field) is not None:
            found = db.execute(text(f"SELECT id FROM {table} WHERE id = :id AND empresa_id = :empresa_id FOR SHARE"),
                               {"id": changes[field], "empresa_id": _empresa_id(tenant)}).first()
            if not found:
                raise ValueError(f"{field}: vínculo não encontrado na empresa atual.")
    if "status" in changes:
        value = (changes["status"] or "").strip().upper()
        if value not in {"ABERTO", "CONCLUIDO", "CANCELADO", "FATURADO"}:
            raise ValueError("Status inválido. Use ABERTO, CONCLUIDO, CANCELADO ou FATURADO.")
        changes["status"] = value
    if "perfil_comercial" in changes:
        value = (changes["perfil_comercial"] or "").strip().upper()
        if value not in {"VAREJO", "DECORADOR", "CONSUMIDOR_FINAL"}:
            raise ValueError("Perfil comercial inválido.")
        changes["perfil_comercial"] = value
    for field, value in changes.items():
        setattr(pedido, field, value)
    db.flush()
    result = _pedido_dict(pedido)
    db.commit()
    return result


def _verificar_vinculos_exclusao(db, pedido_id):
    from sqlalchemy import inspect, text
    inspector = inspect(db.connection())
    # Inspeção do esquema real: inclui vínculos com e sem FK, inclusive RT/OS.
    for schema in inspector.get_schema_names():
        if schema == "information_schema" or schema.startswith("pg_"):
            continue
        for table in inspector.get_table_names(schema=schema):
            if table in {"pedidos", "pedidos_itens"} and schema == "public":
                continue
            columns = {c["name"] for c in inspector.get_columns(table, schema=schema)}
            references = {"pedido_id"} if "pedido_id" in columns else set()
            item_references = {name for name in ("pedido_item_id", "pedido_itens_id") if name in columns}
            for fk in inspector.get_foreign_keys(table, schema=schema):
                if fk.get("referred_table") == "pedidos":
                    references.update(fk["constrained_columns"])
                elif fk.get("referred_table") == "pedidos_itens":
                    item_references.update(fk["constrained_columns"])
            quote = db.get_bind().dialect.identifier_preparer.quote
            for column in references:
                sql = f"SELECT 1 FROM {quote(schema)}.{quote(table)} WHERE {quote(column)} = :id LIMIT 1"
                if db.execute(text(sql), {"id": pedido_id}).first():
                    kind = "lançamento financeiro" if table == "financeiro" else f"registro em {schema}.{table}"
                    raise ValueError(f"Venda não pode ser excluída porque possui {kind} vinculado.")
            for column in item_references:
                sql = f"SELECT 1 FROM {quote(schema)}.{quote(table)} WHERE {quote(column)} IN (SELECT id FROM pedidos_itens WHERE pedido_id = :id) LIMIT 1"
                if db.execute(text(sql), {"id": pedido_id}).first():
                    raise ValueError(f"Venda não pode ser excluída porque seus itens possuem registro em {schema}.{table} vinculado.")


def remover(db, pedido_id, tenant):
    pedido = _pedido_para_alteracao(db, pedido_id, tenant)
    if pedido is None:
        return False
    _verificar_vinculos_exclusao(db, pedido.id)
    if pedido.orcamento_id is not None:
        raise ValueError("Venda não pode ser excluída porque possui orçamento de origem. A exclusão liberaria uma segunda conversão; é necessário definir uma regra de histórico antes.")
    try:
        db.delete(pedido)  # Apenas itens acompanham a venda pela relação existente.
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def criar(db: Session, data, tenant):
    """Cria venda manual em uma única transação, sem orçamento ou financeiro."""
    from sqlalchemy import text
    from types import SimpleNamespace
    from app.services.composicao_comercial import calcular_itens, calcular_composicao
    try:
        empresa_id = _empresa_id(tenant)
        _validar_rt_representante(data.representante_id, data.incluir_rt,
                                 data.percentual_rt, data.valor_rt)
        cliente_final = {key: getattr(data, key) for key in CLIENTE_FINAL_CAMPOS}
        validar_origem_comercial(data.cliente_id, data.parceiro_id, cliente_final)
        for campo, tabela, ativo in (
            ("cliente_id", "clientes", False),
            ("vendedor_id", "funcionarios", False),
            ("parceiro_id", "parceiros_comerciais", True),
            ("representante_id", "representantes", True),
        ):
            value = getattr(data, campo)
            if value is not None:
                condition = " AND ativo = TRUE" if ativo else ""
                row = db.execute(text(f"SELECT id FROM {tabela} WHERE id = :id AND empresa_id = :empresa_id{condition}"),
                                 {"id": value, "empresa_id": empresa_id}).first()
                if row is None:
                    raise ValueError(f"{campo}: registro não encontrado ou inativo para esta empresa.")
        if not data.itens:
            raise ValueError("Inclua pelo menos um item válido.")
        from app.models.produto import ProdutoDB
        from app.services.composicao_comercial import MODELOS_POR_AREA
        for item in data.itens:
            if item.produto_id is None:
                continue
            product = db.query(ProdutoDB).filter(ProdutoDB.id == item.produto_id,
                                                ProdutoDB.empresa_id == empresa_id).first()
            if product is None:
                raise ValueError(f"Produto {item.produto_id} não encontrado para a empresa ativa")
            # Modelo de catálogo define a cobrança; não permite driblar medidas pelo payload.
            model = str(product.modelo_tecnico or "").strip().upper()
            if model in MODELOS_POR_AREA:
                if item.largura <= 0 or item.altura <= 0:
                    raise ValueError("Informe largura e altura maiores que zero para o produto.")
                if item.quantidade != int(item.quantidade):
                    raise ValueError("Produtos por medida exigem quantidade inteira de peças.")
            item.modelo_tecnico = product.modelo_tecnico or item.modelo_tecnico
        calculated = SimpleNamespace(itens=[])
        calcular_itens(db, calculated, data, empresa_id, PedidoItemDB)
        calcular_composicao(calculated, data)
        fields = ("total", "total_final", "percentual_parceiro", "incluir_rt", "tipo_rt",
                  "percentual_rt", "valor_rt", "incluir_taxa_bancaria", "taxa_bancaria_percentual",
                  "valor_parceiro", "valor_taxa_bancaria", "total_cliente_final")
        header = data.dict(exclude=set(fields) | {"itens"})
        # Parâmetros calculados explicitamente, inclusive zero/false quando desligados.
        pedido = PedidoDB(empresa_id=empresa_id, orcamento_id=None, numero=None,
                          **header, **{key: getattr(calculated, key) for key in fields})
        pedido.data_venda = data.data_venda or date.today()
        pedido.itens = calculated.itens
        db.add(pedido)
        db.flush()
        # A PK é alocada pela sequência do banco: segura também entre conversões e criações concorrentes.
        pedido.numero = f"VEN-{pedido.id:06d}"
        db.flush()
        result = _pedido_dict(pedido)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def _validar_rt_representante(representante_id, incluir_rt, percentual_rt, valor_rt):
    if representante_id is None and (
        incluir_rt or _decimal(percentual_rt) != 0 or _decimal(valor_rt) != 0
    ):
        raise ValueError("Selecione um representante para informar RT.")
