"""Regras compartilhadas de itens e composição; não salva documentos."""
from decimal import Decimal, ROUND_HALF_UP
from app.models.produto import ProdutoDB
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado

ITEM_PERSISTED_FIELDS = {
    "tipo_item",
    "produto_id",
    "servico_id",
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
    "ambiente",
    "calculo_producao_status",
    "dados_tecnicos",
}

MULTIPLICADORES = {"DECORADOR": Decimal("1.5"), "VAREJO": Decimal("2.0"), "CONSUMIDOR_FINAL": Decimal("2.5")}
MODELOS_POR_AREA = {"ROLO", "ROLÔ", "ROLO_MOTORIZADA", "ROLÔ MOTORIZADA", "DOUBLE_VISION", "DOUBLE VISION", "DOUBLE VISION MOTORIZADA", "ROMANA", "ROMANA MOTORIZADA", "ROMANA_TETO", "ROMANA DE TETO"}

UNIDADES_METRO_LINEAR = {"ML", "M", "METRO", "METROLINEAR"}
UNIDADES_METRO_QUADRADO = {"M2", "METROQUADRADO", "MQ"}


def _normalizar_unidade_comercial(unidade):
    texto = str(unidade or "").upper().replace("²", "2")
    return "".join(c for c in texto if c.isalnum())


def calcular_base_comercial(unidade_venda, modelo, largura, area_faturavel, quantidade):
    """Retorna a base de cobrança sem alterar o preço unitário cadastrado."""
    unidade = _normalizar_unidade_comercial(unidade_venda)
    quantidade_d = Decimal(str(quantidade))
    if unidade in UNIDADES_METRO_LINEAR:
        return Decimal(str(largura)) * quantidade_d
    if unidade in UNIDADES_METRO_QUADRADO or modelo in MODELOS_POR_AREA:
        return area_faturavel.area_faturavel_m2
    return quantidade_d

def _dinheiro(valor):
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _custo_referencia_comercial(produto):
    # Referencia comercial aprovada: Screen 5% Standard.
    # Nao altera o custo industrial cadastrado.
    if (
        getattr(produto, "empresa_id", None) == 1
        and getattr(produto, "id", None) in {8, 83}
    ):
        return Decimal("56.6667")

    # Referencia comercial fixa: Screen 3% Importado.
    if (
        getattr(produto, "empresa_id", None) == 1
        and getattr(produto, "id", None) == 84
    ):
        return Decimal("60.00")


    custo = Decimal(str(produto.custo_final or 0))
    if custo <= 0:
        custo = Decimal(str(produto.valor_custo or 0))
    return custo


def _preco_produto(produto, perfil):
    custo = _custo_referencia_comercial(produto)
    if custo > 0:
        return (custo * MULTIPLICADORES[perfil]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _dinheiro(produto.valor_venda)

def _aplicar_preco_comercial(valores, item, preco_sugerido, base):
    """Negociação altera só o item; o simulador técnico continua sendo validado."""
    if not hasattr(item, "preco_unitario_manual"):
        # PedidoCreate mantém o contrato anterior de precificação automática.
        return
    manual = bool(item.preco_unitario_manual)
    if manual:
        preco = Decimal(str(item.preco_unitario)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        valores["preco_unitario"] = preco
        valores["subtotal"] = _dinheiro(max(
            Decimal("0"), Decimal(str(base)) * preco - Decimal(str(item.desconto or 0)),
        ))
    dados = dict(valores.get("dados_tecnicos") or {})
    dados["comercial"] = {
        **(dados.get("comercial") or {}),
        "preco_unitario_manual": manual,
        "preco_unitario_sugerido": float(preco_sugerido),
    }
    valores["dados_tecnicos"] = dados


def _validar_acessorios_rolo(db, itens, tenant_id, perfil):
    from app.services.rolo_receita import listar_acessorios_comando_rolo
    from app.services.rolo_simulacao import RoloSimulacaoInput, _tipo_rolo

    acessorios = [item for item in itens if (item.dados_tecnicos or {}).get("acessorio_rolo") is not None]
    if not acessorios:
        return
    ambientes = {}
    for item in itens:
        if item.tipo_item != "PRODUTO" or not item.produto_id:
            continue
        produto = db.query(ProdutoDB).filter_by(id=item.produto_id, empresa_id=tenant_id).one_or_none()
        if produto is None:
            raise ValueError(f"Produto {item.produto_id} não encontrado para a empresa ativa")
        tipo = _tipo_rolo(produto)
        acionamento = str(item.acionamento or ("motorizado" if tipo == "MOTORIZADA" else "manual")).lower()
        if tipo and acionamento in {"motorizado", "motorizada"}:
            ambiente = str(item.ambiente or "").strip().lower()
            config = (item.dados_tecnicos or {}).get("rolo") or {}
            if not isinstance(config, dict):
                raise ValueError("Configuração técnica Rolô inválida.")
            if Decimal(str(item.quantidade)) != Decimal(int(item.quantidade)):
                raise ValueError("Rolô exige quantidade inteira de peças.")
            ambientes.setdefault(ambiente, []).append(RoloSimulacaoInput(
                produto_id=item.produto_id, largura=item.largura, altura=item.altura,
                quantidade=int(item.quantidade), perfil_comercial=perfil, desconto=item.desconto,
                cor=item.cor, acionamento="motorizado", motor_produto_id=config.get("motor_produto_id"),
                kit_produto_id=config.get("kit_produto_id"),
            ))
    por_ambiente = {}
    for item in acessorios:
        config = item.dados_tecnicos["acessorio_rolo"]
        if config != {"vinculo": "AMBIENTE"} or item.tipo_item != "PRODUTO" or not item.produto_id:
            raise ValueError("Configuração de acessório Rolô inválida.")
        if Decimal(str(item.quantidade)) != Decimal(int(item.quantidade)):
            raise ValueError("Acessório Rolô exige quantidade inteira em unidades.")
        ambiente = str(item.ambiente or "").strip().lower()
        if not ambiente or ambiente not in ambientes:
            raise ValueError("Acessório Rolô exige ambiente com persiana motorizada.")
        if ambiente not in por_ambiente:
            por_ambiente[ambiente] = {
                a["produto_id"] for a in listar_acessorios_comando_rolo(db, ambientes[ambiente], tenant_id)
            }
        if item.produto_id not in por_ambiente[ambiente]:
            raise ValueError("Acessório incompatível com as persianas motorizadas do ambiente.")


def calcular_itens(db, o, data, tenant_id, item_model):
    from types import SimpleNamespace
    from app.models.servico import ServicoDB
    from app.services.servico_service import calcular_preco_altura

    existentes = {item.id: item for item in (getattr(o, "itens", None) or []) if getattr(item, "id", None)}
    informados = [item.id for item in data.itens if getattr(item, "id", None) is not None]
    if len(informados) != len(set(informados)) or any(item_id not in existentes for item_id in informados):
        raise ValueError("Identidade de item inválida ou duplicada para este orçamento.")
    if any((item.dados_tecnicos or {}).get("acessorio_rolo") is not None
           and (not getattr(item, "id", None) or getattr(item, "recalcular", False))
           for item in data.itens):
        _validar_acessorios_rolo(db, data.itens, tenant_id, data.perfil_comercial)
    servicos_existentes = {
        item.servico_id for item in (getattr(o, "itens", None) or [])
        if getattr(item, "servico_id", None) is not None
    }
    documento = o
    o = SimpleNamespace(itens=[])
    total = Decimal("0")
    for item in data.itens:
        anterior = existentes.get(getattr(item, "id", None))
        if anterior is not None and not getattr(item, "recalcular", False):
            campos_numericos = ("quantidade", "largura", "altura", "preco_unitario", "desconto")
            campos_identidade = ("tipo_item", "produto_id", "servico_id")
            campos_opcionais = ("unidade", "cor", "acionamento")
            if (any(Decimal(str(getattr(item, campo) or 0)) != Decimal(str(getattr(anterior, campo) or 0))
                    for campo in campos_numericos)
                    or any(getattr(item, campo) != getattr(anterior, campo) for campo in campos_identidade)
                    or any(str(getattr(item, campo) or "").strip().casefold()
                           != str(getattr(anterior, campo) or "").strip().casefold()
                           for campo in campos_opcionais)):
                raise ValueError("Item histórico alterado: solicite o recálculo explícito antes de salvar.")
            total += Decimal(str(anterior.subtotal))
            o.itens.append(anterior)
            continue
        valores = item.dict(include=ITEM_PERSISTED_FIELDS)
        valores["empresa_id"] = tenant_id
        if item.tipo_item == "SERVICO":
            if item.produto_id is not None:
                raise ValueError("Serviço não deve informar produto.")
            if item.servico_id is not None:
                servico = db.query(ServicoDB).filter(
                    ServicoDB.id == item.servico_id,
                    ServicoDB.empresa_id == tenant_id,
                ).first()
                if servico is None:
                    raise ValueError("Serviço não encontrado para a empresa ativa.")
                if servico.situacao != "ATIVO" and item.servico_id not in servicos_existentes:
                    raise ValueError("Serviço inativo não pode ser incluído em um novo documento.")
                valores["unidade"] = servico.unidade
                manual = bool(getattr(item, "preco_unitario_manual", False))
                preco_padrao = (
                    calcular_preco_altura(servico, Decimal(str(item.altura or 0)) * 100)
                    if servico.tipo_calculo == "FAIXA_ALTURA"
                    else Decimal(str(servico.preco_venda or 0))
                )
                if not manual:
                    valores["preco_unitario"] = preco_padrao
                valores["subtotal"] = max(
                    Decimal("0"),
                    Decimal(str(item.quantidade)) * Decimal(str(valores["preco_unitario"]))
                    - Decimal(str(item.desconto or 0)),
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                dados = dict(valores.get("dados_tecnicos") or {})
                comercial = dict(dados.get("comercial") or {})
                comercial.update(
                    preco_unitario_manual=manual,
                    preco_unitario_sugerido=float(preco_padrao),
                )
                dados["comercial"] = comercial
                valores["dados_tecnicos"] = dados
            else:
                valores["subtotal"] = max(
                    Decimal("0"),
                    Decimal(str(item.quantidade)) * Decimal(str(item.preco_unitario))
                    - Decimal(str(item.desconto or 0)),
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                dados = dict(valores.get("dados_tecnicos") or {})
                comercial = dict(dados.get("comercial") or {})
                comercial["preco_unitario_manual"] = bool(
                    getattr(item, "preco_unitario_manual", False)
                )
                dados["comercial"] = comercial
                valores["dados_tecnicos"] = dados
            total += Decimal(str(valores["subtotal"]))
            o.itens.append(item_model(**valores))
            continue
        if item.servico_id is not None:
            raise ValueError("Produto não deve informar serviço.")
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
            _aplicar_preco_comercial(valores, item, simulacao['preco_unitario'], item.quantidade)
            total += Decimal(str(valores['subtotal']))
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
                _aplicar_preco_comercial(valores, item, simulacao['preco_unitario'], simulacao['area_faturavel_m2'])
                total += Decimal(str(valores['subtotal']))
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
                _aplicar_preco_comercial(valores, item, simulacao['preco_unitario'], simulacao['area_faturavel_m2'])
                total += Decimal(str(valores['subtotal']))
                o.itens.append(item_model(**valores))
                continue
            from app.services.rolo_simulacao import _tipo_rolo, RoloSimulacaoInput
            from app.services.romana_teto_simulacao import simular_romana_teto
            from app.schemas.orcamento import RomanaTetoSimulacaoInput
            from app.services.cortina_simulacao import _produto_cortina_fabricada, simular_cortina, CortinaSimulacaoInput
            modelo_tecnico = str(getattr(produto, 'modelo_tecnico', '') or '').strip().upper().replace('_', ' ')
            rolo = _tipo_rolo(produto)
            simulacao = None
            if rolo or modelo_tecnico in {'ROMANA TETO', 'ROMANA DE TETO'} or _produto_cortina_fabricada(produto):
                if Decimal(str(item.quantidade)) != Decimal(int(item.quantidade)):
                    raise ValueError('O modelo técnico exige quantidade inteira de peças.')
            if rolo in {'MANUAL', 'MOTORIZADA'}:
                from app.services.rolo_receita import simular_rolo_catalogo
                rolo_config = (item.dados_tecnicos or {}).get('rolo') or {}
                if not isinstance(rolo_config, dict):
                    raise ValueError('Configuração técnica Rolô inválida.')
                simulacao = simular_rolo_catalogo(db, produto, RoloSimulacaoInput(
                    produto_id=item.produto_id, largura=item.largura, altura=item.altura,
                    quantidade=int(item.quantidade), perfil_comercial=data.perfil_comercial,
                    desconto=item.desconto, cor=item.cor,
                    acionamento=item.acionamento or ('motorizado' if rolo == 'MOTORIZADA' else 'manual'),
                    lado_comando=item.lado_comando, motor_produto_id=rolo_config.get('motor_produto_id'),
                    kit_produto_id=rolo_config.get('kit_produto_id'),
                    incluir_kit_instalacao=rolo_config.get('incluir_kit_instalacao')), tenant_id)
                if "receita" in simulacao:
                    valores["dados_tecnicos"] = {
                        **(valores.get("dados_tecnicos") or {}),
                        "rolo": {
                            "bitola": simulacao["bitola_tecnica"], "receita": simulacao["receita"],
                            "acionamento": simulacao["acionamento_permitido"],
                            "fabricacao": simulacao["fabricacao_por_peca"],
                            **({
                                "motor_produto_id": simulacao["componentes_tecnicos"]["motor"]["produto_id"],
                                "kit_produto_id": simulacao["componentes_tecnicos"]["acessorios"][0]["produto_id"],
                        "incluir_kit_instalacao": simulacao.get("incluir_kit_instalacao", True),
                                "motor": simulacao["componentes_tecnicos"]["motor"],
                                "carga_pendente": simulacao["componentes_tecnicos"]["motor"].get(
                                    "carga_pendente", False
                                ),
                            } if rolo_config.get("motor_produto_id") is not None else {}),
                        },
                    }
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
                base = item.quantidade if simulacao.get('modelo') == 'CORTINA' else simulacao['area_faturavel_m2']
                _aplicar_preco_comercial(valores, item, simulacao['preco_unitario'], base)
                total += Decimal(str(valores['subtotal']))
                o.itens.append(item_model(**valores))
                continue
            preco = _preco_produto(produto, data.perfil_comercial)
            if (item.dados_tecnicos or {}).get("acessorio_rolo") is not None:
                valores.update(unidade="UN", modelo_tecnico=None, area=0, preco_unitario=preco,
                               subtotal=_dinheiro(max(Decimal("0"), Decimal(str(item.quantidade)) * preco
                                                       - Decimal(str(item.desconto or 0)))))
                _aplicar_preco_comercial(valores, item, preco, item.quantidade)
                total += Decimal(str(valores["subtotal"]))
                o.itens.append(item_model(**valores))
                continue
            modelo = str(item.modelo_tecnico or produto.modelo_tecnico or "").strip().upper()

            # Usa regra central de área faturável (mínimo 1,50 m² para produtos vendidos em M²)
            unidade_venda = getattr(produto, 'unidade_venda', None)
            area_faturavel: AreaFaturavelResultado = calcular_area_faturavel(
                largura=item.largura,
                altura=item.altura,
                quantidade=item.quantidade,
                unidade_venda=unidade_venda,
            )

            # A unidade comercial prevalece: ML usa comprimento, M² usa área e
            # as demais unidades usam quantidade. O modelo mantém a compatibilidade
            # dos produtos por área que ainda não possuem unidade normalizada.
            base = calcular_base_comercial(
                unidade_venda=unidade_venda,
                modelo=modelo,
                largura=item.largura,
                area_faturavel=area_faturavel,
                quantidade=item.quantidade,
            )

            subtotal = max(Decimal("0"), (base * preco) - Decimal(str(item.desconto or 0)))
            valores["preco_unitario"] = preco
            valores["subtotal"] = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Salva também a área real e faturável para auditoria
            valores["area"] = float(area_faturavel.area_real_m2)
            _aplicar_preco_comercial(valores, item, preco, base)
        else:
            subtotal = max(Decimal("0"), Decimal(str(item.quantidade)) * Decimal(str(item.preco_unitario)) - Decimal(str(item.desconto or 0)))
            valores["subtotal"] = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            comercial = (item.dados_tecnicos or {}).get("comercial") or {}
            sugerido = comercial.get("preco_unitario_sugerido", item.preco_unitario)
            _aplicar_preco_comercial(valores, item, sugerido, item.quantidade)
        total += Decimal(str(valores["subtotal"]))
        o.itens.append(item_model(**valores))
    final = []
    for entrada, calculado in zip(data.itens, o.itens):
        anterior = existentes.get(getattr(entrada, "id", None))
        if anterior is calculado:
            anterior.descricao = entrada.descricao
            anterior.observacao_item = entrada.observacao_item
            anterior.ambiente = entrada.ambiente
        if anterior is not None and anterior is not calculado:
            for campo in ITEM_PERSISTED_FIELDS | {"empresa_id"}:
                setattr(anterior, campo, getattr(calculado, campo, None))
            final.append(anterior)
        else:
            final.append(calculado)
    documento.itens[:] = final
    documento.total = total.quantize(
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
