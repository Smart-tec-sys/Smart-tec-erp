"""Serviço de simulação técnica do Rolô — não persiste nem calcula preço final.
Usa a regra central de seleção de tubo (app.technical.rules.rolo) e o motor
existente de cálculo de produção (app.services.motor_calculo_produtos)."""
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional

from pydantic import BaseModel, Field, conint

from app.technical.rules.rolo import (
    selecionar_tubo_rolo,
    TuboRoloDiametro,
    AcionamentoPermitido,
    MotorObrigatorioErro,
    tubo_para_codigo_tecnico,
)
from app.services.motor_calculo_produtos import (
    calcular_produto_sob_medida,
    ResultadoCalculoProduto,
)
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado


class RoloSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    largura: float = Field(gt=0, allow_inf_nan=False)
    altura: float = Field(gt=0, allow_inf_nan=False)
    quantidade: conint(strict=True, gt=0)
    perfil_comercial: Literal['DECORADOR', 'VAREJO', 'CONSUMIDOR_FINAL'] = 'VAREJO'
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    cor: Optional[str] = None
    acionamento: Literal['manual', 'motorizado'] = 'manual'
    lado_comando: Optional[str] = None


def _tipo_rolo(produto) -> Optional[str]:
    """Classifica o produto final; evidencias de componente tem precedencia."""
    import re
    import unicodedata

    def normalizar(value) -> str:
        texto = ''.join(
            c for c in unicodedata.normalize('NFKD', str(value or ''))
            if not unicodedata.combining(c)
        ).upper().replace('_', ' ')
        return ' '.join(texto.split())

    campos = {
        campo: normalizar(getattr(produto, campo, None))
        for campo in (
            'nome', 'modelo_tecnico', 'modelo', 'grupo_produto',
            'grupo_tecnico', 'familia_tecnica', 'tipo_produto', 'unidade_venda',
        )
    }
    # No DEV ha componentes com modelo ROLO, unidade M2 e composicao Sim.
    # Nenhum desses atributos pode sobrepor uma classificacao de componente.
    componentes = {
        'COMPONENTE', 'COMPONENTES', 'ACESSORIO', 'ACESSORIOS',
        'INSUMO', 'INSUMOS', 'PECA', 'PECAS', 'MATERIA', 'SEMIACABADO',
        'TEC', 'TECIDO', 'TECIDOS', 'TUBO', 'TUBOS', 'COMANDO', 'COMANDOS',
        'SUPORTE', 'SUPORTES', 'BASE', 'BASES', 'CORRENTE', 'CORRENTES',
        'PONTEIRA', 'PONTEIRAS', 'TAMPA', 'TAMPAS', 'PERFIL', 'PERFIS',
        'MOTOR', 'MOTORES', 'MOTORIZACAO', 'KIT', 'KITS', 'EIXO', 'EIXOS',
        'BANDO', 'GUIA', 'GUIAS', 'EMENDA', 'CLIP', 'CLIPS', 'FITA',
        'ESPAGUETE', 'CAVALETE', 'BARRA', 'LAMINA', 'LAMINAS',
    }
    for campo in campos:
        if campo == 'unidade_venda':
            continue
        if componentes.intersection(re.findall(r'[A-Z0-9]+', campos[campo])):
            return None

    modelo = campos['modelo_tecnico']
    modelos_rolo = {'ROLO', 'ROLO MANUAL', 'ROLO MOTORIZADA', 'ROLO MOTORIZADO'}
    if modelo and modelo not in modelos_rolo:
        return None

    if modelo not in modelos_rolo:
        # Fallback restrito ao cadastro comercial legado, sem sinais conflitantes.
        if campos['grupo_produto'] not in {'PERSIANAS', 'ROLO'}:
            return None
        if campos['unidade_venda'] not in {'M2', 'METRO QUADRADO'}:
            return None
        if campos['tipo_produto'] not in {'', 'PRODUTO FABRICADO'}:
            return None
        if campos['grupo_tecnico'] not in {'', 'PERSIANA ROLO'}:
            return None
        familia = campos['familia_tecnica']
        if familia and familia != 'ROLO' and not familia.startswith('ROLO '):
            return None
        if campos['modelo'] not in {'', 'MANUAL', 'MOTORIZADA', 'MOTORIZADO'} | modelos_rolo:
            return None
        if not re.match(r'^ROLO (?:SCREEN|BLACKOUT|BK|TRANSLUCIDA|TRANSLUCIDO)(?:\b|[.])', campos['nome']):
            return None

    texto = ' '.join(campos[campo] for campo in ('modelo_tecnico', 'modelo', 'nome'))
    if re.search(r'\bMOTORIZAD[AO]\b', texto):
        return 'MOTORIZADA'
    return 'MANUAL'


def _montar_catalogo_rolo(tubo_diametro: TuboRoloDiametro) -> dict:
    """Monta catálogo mínimo para o motor de cálculo com o tubo selecionado."""
    tubo_codigo = tubo_para_codigo_tecnico(tubo_diametro)
    comando_codigo = f"COMANDO_{tubo_diametro.value.replace('mm', 'MM')}"

    return {
        "tecido": {"codigo": "TEC_ROLO", "nome": "Tecido Rolô", "unidade": "M²", "valor_custo": 0},
        "fita_tubo": {"codigo": "FITA_TUBO", "nome": "Fita tubo", "unidade": "ML", "valor_custo": 0},
        "base": {"codigo": "BASE_ROLO", "nome": "Base", "unidade": "ML", "valor_custo": 0},
        "fita_base": {"codigo": "FITA_BASE", "nome": "Fita base", "unidade": "ML", "valor_custo": 0},
        "espaguete_base": {"codigo": "ESPAGUETE_BASE", "nome": "Espaguete base", "unidade": "ML", "valor_custo": 0},
        "corrente": {"codigo": "CORRENTE_ROLO", "nome": "Corrente", "unidade": "ML", "valor_custo": 0},
        "emenda_corrente": {"codigo": "EMEDA_CORRENTE", "nome": "Emenda corrente", "unidade": "UN", "valor_custo": 0},
        "tampa_base": {"codigo": "TAMPA_BASE", "nome": "Tampa base", "unidade": "UN", "valor_custo": 0},
        tubo_codigo: {"codigo": tubo_codigo, "nome": f"Tubo {tubo_diametro.value}", "unidade": "ML", "valor_custo": 0},
        comando_codigo: {"codigo": comando_codigo, "nome": f"Comando {tubo_diametro.value}", "unidade": "KIT", "valor_custo": 0},
    }


def _extrair_componentes_rolo(resultado: ResultadoCalculoProduto, tubo_diametro: TuboRoloDiametro, acionamento: str) -> dict:
    """Extrai componentes técnicos do resultado do motor para resposta legível."""
    componentes = {item.categoria: item for item in resultado.componentes}

    return {
        "bitola_selecionada": tubo_diametro.value,
        "tubo": {
            "codigo": tubo_para_codigo_tecnico(tubo_diametro),
            "diametro": tubo_diametro.value,
            "quantidade_ml": round(componentes.get("Tubo", {}).quantidade, 4) if "Tubo" in componentes else 0,
        },
        "comando": {
            "tipo": acionamento,
            "compatibilidade": "compatível" if acionamento == "manual" else "motorizado",
            "observacao": "Kit comando ação premium" if acionamento == "manual" else "Motor e controle a confirmar",
        },
        "tecido": {
            "quantidade_m2": round(componentes.get("Tecido", {}).quantidade, 4) if "Tecido" in componentes else 0,
            "regra": "Largura -3cm x altura +15cm",
        },
        "base": {
            "quantidade_ml": round(componentes.get("Perfil/Base", {}).quantidade, 4) if "Perfil/Base" in componentes else 0,
        },
        "corrente": {
            "quantidade_ml": round(componentes.get("Corrente", {}).quantidade, 4) if "Corrente" in componentes else 0,
            "regra": "Altura dupla, máx. 3m",
        },
        "emenda_corrente": {
            "quantidade_un": round(componentes.get("Emenda corrente", {}).quantidade, 4) if "Emenda corrente" in componentes else 0,
        },
        "tampas": {
            "quantidade_un": round(componentes.get("Tampa da base", {}).quantidade, 4) if "Tampa da base" in componentes else 0,
        },
        "suportes": {
            "observacao": "CLIPS/SUPORTES conforme largura (até 1m=2; +1 a cada 50cm)",
        },
        "ponteira": {
            "observacao": "Tampa redonda do eixo (par fixo)",
        },
        "bando_guias": {
            "aplicavel": False,
            "observacao": "Bandô/guias não padrão para Rolô; verificar se item comercial inclui.",
        },
    }


def _catalogo_da_receita(receita: dict, diametro: TuboRoloDiametro) -> dict:
    """Usa exclusivamente os insumos da receita vinculada à empresa ativa."""
    bitola = diametro.value
    componentes = receita.get("componentes") or {}
    referencias = {
        "tecido": receita.get("tecido"),
        "tubo": (receita.get("tubos") or {}).get(bitola),
        "comando": (receita.get("comandos") or {}).get(bitola),
        **{nome: componentes.get(nome) for nome in (
            "base", "fita_tubo", "fita_base", "espaguete_base",
            "corrente", "emenda_corrente", "tampa_base",
        )},
    }
    catalogo = {}
    for nome, item in referencias.items():
        if not isinstance(item, dict):
            raise ValueError(f"Receita técnica incompleta: falta {nome} para tubo {bitola}.")
        preco = Decimal(str(item.get("preco_compra") or 0))
        embalagem = Decimal(str(item.get("unidades_por_compra") or 0))
        if preco <= 0 or embalagem <= 0:
            raise ValueError(f"Componente {nome} sem custo ou unidade de compra válida na receita.")
        ipi = Decimal(str(item.get("ipi_percentual") or 0))
        unitario = preco * (Decimal("1") + ipi / Decimal("100")) / embalagem
        catalogo[nome] = {
            "codigo": str(item.get("codigo_interno") or ""),
            "nome": nome.replace("_", " ").title(),
            "unidade": item.get("unidade_tecnica") or "UN",
            "custo_unitario": float(unitario),
        }
    # O motor de produção consome a chave genérica 'tubo' e 'comando'.
    return catalogo


def _custo_picasso(fabricacao: ResultadoCalculoProduto, receita: dict, altura: float, quantidade: int) -> Decimal:
    """Tecido Picasso por faixa integral ML; demais componentes pelas quantidades da receita."""
    if receita.get("custeio_tecido") != "FAIXA_INTEGRAL_ML":
        return Decimal(str(fabricacao.custo_total))
    tecido = receita["tecido"]
    preco_ml = Decimal(str(tecido["preco_compra"]))
    ipi = Decimal(str(tecido.get("ipi_percentual") or 0))
    # A receita usa largura de bobina de 2,50m: cada peça consome faixa inteira.
    largura_bobina = Decimal(str(receita.get("largura_bobina_m") or 0))
    if largura_bobina <= 0:
        raise ValueError("Receita sem largura da bobina para custeio de faixa integral.")
    if Decimal(str(fabricacao.largura)) > largura_bobina:
        raise ValueError("Largura da peça excede a bobina; exige validação técnica de emenda.")
    faixa_ml = (Decimal(str(altura)) + Decimal("0.15")) * Decimal("1.05") * Decimal(quantidade)
    custo_tecido = faixa_ml * preco_ml * (Decimal("1") + ipi / Decimal("100"))
    outros = sum((Decimal(str(c.custo_total)) for c in fabricacao.componentes if c.categoria != "Tecido"), Decimal("0"))
    return custo_tecido + outros


def simular_rolo(produto, entrada: RoloSimulacaoInput, receita: Optional[dict] = None) -> dict:
    """Executa a simulação técnica do Rolô.

    Retorna erro 422 (ValueError) para combinação técnica inválida (ex.: manual >3,20m).
    """
    tipo = _tipo_rolo(produto)
    if tipo not in ('MANUAL', 'MOTORIZADA'):
        raise ValueError('Simulação disponível somente para produtos Rolô final (manual ou motorizada).')

    # Valida acionamento coerente com o produto
    if tipo == 'MANUAL' and entrada.acionamento == 'motorizado':
        raise ValueError('Produto é Rolô manual; não simular como motorizado.')
    if tipo == 'MOTORIZADA' and entrada.acionamento == 'manual':
        raise ValueError('Produto é Rolô motorizada; acionamento manual não se aplica.')

    # Seleção técnica do tubo pela regra central
    try:
        selecao = selecionar_tubo_rolo(entrada.largura, acionamento=entrada.acionamento)
    except MotorObrigatorioErro as exc:
        raise ValueError(str(exc)) from exc

    # Motor de cálculo de produção (custo técnico)
    catalogo = _catalogo_da_receita(receita, selecao.diametro) if receita else _montar_catalogo_rolo(selecao.diametro)
    opcoes = {
        "perda_tecido_percentual": 5.0,
        "desconto_largura_tubo_base": 0.025,
        "desconto_largura_tecido": 0.03,
        "sobra_altura_tecido": 0.15,
    }
    fabricacao = calcular_produto_sob_medida(
        "Rolô",
        entrada.largura,
        entrada.altura,
        entrada.quantidade,
        catalogo=catalogo,
        opcoes=opcoes,
    )

    if min(getattr(fabricacao, 'largura', 0), getattr(fabricacao, 'altura', 0)) <= 0:
        raise ValueError('Medidas produzem cortes não positivos; revise largura e altura.')

    # Preço comercial (usa regra atual do backend via orcamento_service)
    from app.services.orcamento_service import _preco_produto, _dinheiro
    preco = _preco_produto(produto, entrada.perfil_comercial)
    custo_receita = None
    if receita:
        from app.services.composicao_comercial import MULTIPLICADORES
        custo_total_receita = _custo_picasso(fabricacao, receita, entrada.altura, entrada.quantidade)
        custo_receita = (custo_total_receita / Decimal(entrada.quantidade))
        # O preço unitário é por m² faturável, não por peça.
        area = calcular_area_faturavel(largura=entrada.largura, altura=entrada.altura,
                                      quantidade=entrada.quantidade, unidade_venda=getattr(produto, 'unidade_venda', None))
        if area.area_faturavel_m2 <= 0:
            raise ValueError("Área faturável inválida.")
        preco = (custo_total_receita * MULTIPLICADORES[entrada.perfil_comercial] / area.area_faturavel_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    custo = next((Decimal(str(getattr(produto, campo, 0) or 0))
                  for campo in ('custo_final', 'valor_custo')
                  if Decimal(str(getattr(produto, campo, 0) or 0)) > 0), None)

    # Área faturável (regra central: mínimo 1,50 m² apenas para produtos vendidos em M²)
    unidade_venda = getattr(produto, 'unidade_venda', None)
    area_faturavel: AreaFaturavelResultado = calcular_area_faturavel(
        largura=entrada.largura,
        altura=entrada.altura,
        quantidade=entrada.quantidade,
        unidade_venda=unidade_venda,
    )
    subtotal = _dinheiro(max(Decimal('0'), area_faturavel.area_faturavel_m2 * preco - Decimal(str(entrada.desconto))))

    avisos = list(fabricacao.alertas)
    if custo is None and not receita:
        avisos.append('Sem custo cadastrado: preço comercial segue regra do backend sem novo acréscimo.')
    if preco <= 0:
        avisos.append('Preço indisponível: cadastro sem custo ou valor de venda positivo. Revise antes de salvar.')

    # Alertas técnicos específicos do Rolô
    if selecao.requer_confirmacao_vendedor:
        avisos.append(f'ATENÇÃO: {selecao.observacao}')
    if selecao.acionamento_permitido == AcionamentoPermitido.MOTORIZADO:
        avisos.append('Motorização obrigatória para largura > 3,20m. Torque e motor não calculados automaticamente.')

    componentes_tecnicos = _extrair_componentes_rolo(fabricacao, selecao.diametro, entrada.acionamento)

    return dict(
        modelo='ROLÔ',
        tipo_acionamento=tipo,
        quantidade_pecas=entrada.quantidade,
        area_real_m2=area_faturavel.area_real_m2,
        area_faturavel_m2=area_faturavel.area_faturavel_m2,
        minimo_faturavel_aplicado=area_faturavel.minimo_faturavel_aplicado,
        bitola_tecnica=selecao.diametro.value,
        acionamento_permitido=selecao.acionamento_permitido.value,
        requer_confirmacao_vendedor=selecao.requer_confirmacao_vendedor,
        observacao_tecnica=selecao.observacao,
        fabricacao_por_peca=asdict(fabricacao),
        componentes_tecnicos=componentes_tecnicos,
        custo_tecnico=round(float(custo_total_receita), 4) if receita else (round(float(fabricacao.custo_total), 4) if fabricacao.custo_total > 0 else None),
        custo_cadastrado=float(custo_receita) if custo_receita is not None else (float(custo) if custo is not None else None),
        preco_unitario=preco,
        subtotal=subtotal,
        preco_disponivel=preco > 0,
        alertas=avisos,
        origem_preco='RECEITA_TECNICA_EMPRESA' if receita else ('CUSTO_CADASTRADO' if custo is not None else 'VALOR_VENDA_CADASTRADO'),
        aviso='Simulação técnica recalculada por peça; não representa histórico nem composição integral precificada. Custo técnico só disponível quando componentes/equivalências válidas existirem no catálogo.',
    )