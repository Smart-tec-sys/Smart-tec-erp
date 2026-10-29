"""Regras compartilhadas de itens e composição; não salva documentos."""
from decimal import Decimal, ROUND_HALF_UP
from app.models.produto import ProdutoDB
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado

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

def calcular_itens(db, o, data, tenant_id, item_model):
    o.itens.clear()
    total = Decimal("0")
    for item in data.itens:
        valores = item.dict(include=ITEM_PERSISTED_FIELDS)
        if str(item.modelo_tecnico or '').strip().upper() == 'CORTINA':
            from app.services.cortina_simulacao import entrada_cortina_item, simular_cortina_catalogo
            simulacao = simular_cortina_catalogo(db, entrada_cortina_item(item, data.perfil_comercial), tenant_id)
            if not simulacao['preco_disponivel']:
                raise ValueError('Cortina: tecido/forro sem custo técnico disponível.')
            config = dict((item.dados_tecnicos or {}).get('cortina') or {})
            config['result'] = simulacao
            valores.update(preco_unitario=simulacao['preco_unitario'], subtotal=simulacao['subtotal'],
                           dados_tecnicos={**(item.dados_tecnicos or {}), 'cortina': config},
                           calculo_producao_status='SIMULACAO_RECALCULADA')
            total += Decimal(str(simulacao['subtotal']))
            o.itens.append(item_model(**valores))
            continue
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
                o.itens.append(item_model(**valores))
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
                o.itens.append(item_model(**valores))
                continue
            from app.services.rolo_simulacao import _tipo_rolo, simular_rolo, RoloSimulacaoInput
            from app.services.romana_teto_simulacao import simular_romana_teto
            from app.schemas.orcamento import RomanaTetoSimulacaoInput
            from app.services.cortina_simulacao import _produto_cortina_fabricada, simular_cortina, CortinaSimulacaoInput
            modelo_tecnico = str(getattr(produto, 'modelo_tecnico', '') or '').strip().upper().replace('_', ' ')
            rolo = _tipo_rolo(produto)
            simulacao = None
            if rolo or modelo_tecnico in {'ROMANA TETO', 'ROMANA DE TETO'} or _produto_cortina_fabricada(produto):
                if Decimal(str(item.quantidade)) != Decimal(int(item.quantidade)):
                    raise ValueError('O modelo técnico exige quantidade inteira de peças.')
            if rolo == 'MOTORIZADA':
                raise ValueError('Rolô motorizada: cálculo técnico não liberado.')
            if rolo == 'MANUAL':
                simulacao = simular_rolo(produto, RoloSimulacaoInput(
                    produto_id=item.produto_id, largura=item.largura, altura=item.altura,
                    quantidade=int(item.quantidade), perfil_comercial=data.perfil_comercial,
                    desconto=item.desconto, cor=item.cor, acionamento=item.acionamento or 'manual',
                    lado_comando=item.lado_comando))
            elif modelo_tecnico in {'ROMANA TETO', 'ROMANA DE TETO'}:
                config = (item.dados_tecnicos or {}).get('romana_teto', {})
                simulacao = simular_romana_teto(produto, RomanaTetoSimulacaoInput(
                    produto_id=item.produto_id, largura_modulo_m=item.largura,
                    comprimento_avanco_m=item.altura, quantidade_modulos=int(item.quantidade),
                    perfil_comercial=data.perfil_comercial, desconto=item.desconto, cor=item.cor,
                    acionamento=config.get('acionamento') or getattr(item, 'acionamento_romana_teto', None) or item.acionamento or 'MANUAL_BASTAO',
                    lado_comando=config.get('lado_comando') or item.lado_comando,
                    comprimento_bastao_m=config.get('comprimento_bastao_m') or getattr(item, 'comprimento_bastao_m', None),
                    comprimento_corrente_sem_fim_m=config.get('comprimento_corrente_sem_fim_m') or getattr(item, 'comprimento_corrente_sem_fim_m', None)))
            elif _produto_cortina_fabricada(produto):
                config = (item.dados_tecnicos or {}).get('cortina')
                if not config:
                    raise ValueError('Configure os dados técnicos da Cortina antes de salvar.')
                from app.services.cortina_simulacao import entrada_cortina_item, simular_cortina_catalogo
                simulacao = simular_cortina_catalogo(db, entrada_cortina_item(item, data.perfil_comercial), tenant_id)
            if simulacao is not None:
                if not simulacao['preco_disponivel']:
                    raise ValueError('Preço técnico indisponível. Revise a cor, as medidas e o cadastro do produto.')
                valores.update(preco_unitario=simulacao['preco_unitario'], subtotal=simulacao['subtotal'],
                               area=simulacao.get('area_real_m2', item.area), calculo_producao_status='SIMULACAO_RECALCULADA')
                total += Decimal(str(simulacao['subtotal']))
                o.itens.append(item_model(**valores))
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
        o.itens.append(item_model(**valores))
    o.total = total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def calcular_composicao(o, data):
    o.total_final = max(
        Decimal("0"),
        o.total - Decimal(str(data.desconto or 0)),
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    percentual_parceiro = Decimal(str(data.percentual_parceiro or 0))
    if percentual_parceiro < 0 or (data.parceiro_id is None and percentual_parceiro > 0):
        raise ValueError("Selecione o parceiro para aplicar percentual.")
    o.percentual_parceiro = percentual_parceiro
    valor_parceiro = (
        o.total_final
        * percentual_parceiro
        / Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


    # ================================================================
    # RT OPCIONAL
    # ================================================================
    # RT pode ser informado mesmo sem os dados do representante.
    o.incluir_rt = bool(data.incluir_rt)

    if data.incluir_rt:
        tipo_rt = (
            str(data.tipo_rt).strip().upper()
            if data.tipo_rt
            else None
        )

        if tipo_rt not in {
            "VALOR_FIXO",
            "PERCENTUAL",
        }:
            raise ValueError(
                "Informe o tipo do RT."
            )

        percentual_rt = Decimal(
            str(data.percentual_rt or 0)
        )

        valor_rt_fixo = Decimal(
            str(data.valor_rt or 0)
        )

        if tipo_rt == "PERCENTUAL":
            if percentual_rt <= 0:
                raise ValueError(
                    "Informe um percentual de RT maior que zero."
                )

            if percentual_rt > Decimal("100"):
                raise ValueError(
                    "Percentual de RT não pode ser maior que 100%."
                )

            valor_rt = (
                o.total_final
                * percentual_rt
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            valor_rt_fixo = Decimal("0")
        else:
            if valor_rt_fixo <= 0:
                raise ValueError(
                    "Informe um valor de RT maior que zero."
                )

            percentual_rt = Decimal("0")

            valor_rt = valor_rt_fixo.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        o.tipo_rt = tipo_rt
        o.percentual_rt = percentual_rt
        o.valor_rt = valor_rt

    else:
        o.tipo_rt = None
        o.percentual_rt = Decimal("0")
        o.valor_rt = Decimal("0")
        valor_rt = Decimal("0")
    # ================================================================
    # BASE PROTEGIDA
    # Empresa + parceiro + RT
    # ================================================================
    base_protegida = (
        o.total_final
        + valor_parceiro
        + valor_rt
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    # ================================================================
    # TAXA BANCARIA OPCIONAL - CALCULO POR DENTRO
    # ================================================================
    taxa = Decimal(
        str(data.taxa_bancaria_percentual or 0)
    )

    if taxa < 0 or taxa >= 100:
        raise ValueError(
            "Taxa bancária deve ficar entre 0 e menos de 100%."
        )

    o.incluir_taxa_bancaria = bool(
        data.incluir_taxa_bancaria
    )

    if not o.incluir_taxa_bancaria:
        taxa = Decimal("0")

    if taxa > 0:
        fator_liquido = (
            Decimal("1")
            - taxa / Decimal("100")
        )

        total_cliente = (
            base_protegida
            / fator_liquido
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    else:
        total_cliente = base_protegida

    valor_taxa = (
        total_cliente
        - base_protegida
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    o.taxa_bancaria_percentual = taxa
    o.valor_parceiro = valor_parceiro
    o.base_protegida = base_protegida
    o.valor_taxa_bancaria = valor_taxa
    o.total_cliente_final = total_cliente
