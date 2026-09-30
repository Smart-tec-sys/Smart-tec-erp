"""Serviço de simulação técnica Double Vision — não persiste nem calcula preço final.
Usa a regra central de seleção de tubo (app.technical.rules.double_vision) e o motor
existente de cálculo de produção (app.services.motor_calculo_produtos)."""
import math
from dataclasses import asdict
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, conint

from app.technical.rules.double_vision import (
    selecionar_tubo_double_vision,
    TuboDVdiametro,
    EstadoValidacao,
    LarguraExcedidaErro,
    LarguraInvalidaErro,
    tubo_para_codigo_tecnico,
)
from app.services.motor_calculo_produtos import (
    calcular_produto_sob_medida,
    ResultadoCalculoProduto,
)
from app.services.area_faturavel import calcular_area_faturavel, AreaFaturavelResultado


def qtd_grapas_double_vision(largura: float) -> int:
    """
    Double Vision:
    até 1,00m = 2 grapas.
    acima de 1,00m = +1 grapa a cada 50cm.
    """
    try:
        largura_f = float(largura or 0)
    except Exception:
        largura_f = 0.0
    if largura_f <= 1.0:
        return 2
    return max(2, 2 + math.ceil((largura_f - 1.0) / 0.50))


class DoubleVisionSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    largura: float = Field(gt=0, allow_inf_nan=False)
    altura: float = Field(gt=0, allow_inf_nan=False)
    quantidade: conint(strict=True, gt=0)
    perfil_comercial: Literal['DECORADOR', 'VAREJO', 'CONSUMIDOR_FINAL'] = 'VAREJO'
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    com_bando: bool = False
    tem_validacao_tecido_fornecedor: bool = False


def _tipo_double_vision(produto) -> Optional[str]:
    """Detecta se o produto é Double Vision manual pelo modelo_tecnico/nome."""
    def normalizar(value: str) -> str:
        import unicodedata
        return ''.join(
            c for c in unicodedata.normalize('NFD', str(value or ''))
            if not unicodedata.combining(c)
        ).upper().replace('_', ' ')

    modelo = normalizar(getattr(produto, 'modelo_tecnico', ''))
    texto = ' '.join(normalizar(getattr(produto, campo, ''))
                     for campo in ('modelo_tecnico', 'modelo', 'nome'))
    if 'DOUBLE VISION' not in texto:
        return None
    if 'MOTORIZ' in texto:
        return None  # Motorizada não liberada nesta fase
    if modelo in ('DOUBLE VISION', 'DOUBLE VISION MANUAL'):
        return 'MANUAL'
    return None


def _montar_catalogo_double_vision(
    tubo_diametro: TuboDVdiametro,
    com_bando: bool,
) -> dict:
    """Monta catálogo mínimo para o motor de cálculo com o tubo selecionado."""
    tubo_codigo = tubo_para_codigo_tecnico(tubo_diametro)

    return {
        "tecido": {
            "codigo": "TEC_DOUBLE_VISION",
            "nome": "Tecido Double Vision",
            "unidade": "M²",
            "valor_custo": 0,
        },
        "barra_niveladora": {
            "codigo": "BARRA_NIVELADORA_DV",
            "nome": "Barra Niveladora Double Vision",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "bando": {
            "codigo": "BANDO_DOUBLE_VISION",
            "nome": "Bandô Double Vision",
            "unidade": "ML",
            "valor_custo": 0,
        } if com_bando else None,
        "tampa_bando": {
            "codigo": "TAMPA_BANDO_DV",
            "nome": "Tampa Bandô Double Vision",
            "unidade": "UN",
            "valor_custo": 0,
        } if com_bando else None,
        "tubo": {
            "codigo": tubo_codigo,
            "nome": f"Tubo {tubo_diametro.value}",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "comando": {
            "codigo": f"KIT_COMANDO_ACAO_PREMIUM_{tubo_diametro.value.replace('mm', 'MM')}",
            "nome": f"Kit Comando Ação Premium {tubo_diametro.value}",
            "unidade": "KIT",
            "valor_custo": 0,
        },
        "corrente": {
            "codigo": "CORRENTE_JUTA_BOLA_10",
            "nome": "Corrente Juta Bola 10",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "emenda_corrente": {
            "codigo": "EMEDA_CORRENTE",
            "nome": "Emenda Corrente",
            "unidade": "UN",
            "valor_custo": 0,
        },
        "pendulo": {
            "codigo": "PENDULO_CRISTAL",
            "nome": "Pêndulo Cristal",
            "unidade": "UN",
            "valor_custo": 0,
        },
        "eixo_base": {
            "codigo": "EIXO_BASE_DV",
            "nome": "Eixo Base Double Vision",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "base_cunha": {
            "codigo": "BASE_CUNHA_DV",
            "nome": "Base Cunha Double Vision",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "tampa_eixo": {
            "codigo": "TAMPA_EIXO_DV",
            "nome": "Tampa Redonda do Eixo Double Vision",
            "unidade": "UN",
            "valor_custo": 0,
        },
        "tampa_base": {
            "codigo": "TAMPA_BASE_DV",
            "nome": "Tampa Base Double Vision",
            "unidade": "UN",
            "valor_custo": 0,
        },
        "clips": {
            "codigo": "CLIPS_GRAPA_40MM",
            "nome": "CLIPS E SUPORTES - GRAPA 40MM BRANCA - IMPORTADA",
            "unidade": "UN",
            "valor_custo": 0,
        },
        "espaguete": {
            "codigo": "ESPAGUETE_2_5MM",
            "nome": "Espaguete 2,5mm",
            "unidade": "ML",
            "valor_custo": 0,
        },
        "fita_plastica": {
            "codigo": "FITA_PLASTICA_1_5MM",
            "nome": "Fita Plástica 1,5mm",
            "unidade": "ML",
            "valor_custo": 0,
        },
    }


def _extrair_componentes_double_vision(
    resultado: ResultadoCalculoProduto,
    tubo_diametro: TuboDVdiametro,
    com_bando: bool,
    largura: float,
) -> dict:
    """Extrai componentes técnicos do resultado do motor para resposta legível."""
    componentes = {item.categoria: item for item in resultado.componentes}

    qtd_clips = qtd_grapas_double_vision(largura)

    return {
        "bitola_selecionada": tubo_diametro.value,
        "tubo": {
            "codigo": tubo_para_codigo_tecnico(tubo_diametro),
            "diametro": tubo_diametro.value,
            "quantidade_ml": round(componentes.get("Tubo", {}).quantidade, 4) if "Tubo" in componentes else 0,
        },
        "tecido": {
            "quantidade_m2": round(componentes.get("Tecido", {}).quantidade, 4) if "Tecido" in componentes else 0,
            "regra": "Largura -2,5cm x altura dupla +15cm",
            "consumo_camada_dupla": True,
        },
        "barra_niveladora": {
            "aplicavel": not com_bando,
            "quantidade_ml": round(componentes.get("Barra Niveladora", {}).quantidade, 4) if "Barra Niveladora" in componentes else 0,
        } if not com_bando else None,
        "bando": {
            "aplicavel": com_bando,
            "quantidade_ml": round(componentes.get("Bandô", {}).quantidade, 4) if "Bandô" in componentes else 0,
        } if com_bando else None,
        "corrente": {
            "quantidade_ml": round(componentes.get("Corrente", {}).quantidade, 4) if "Corrente" in componentes else 0,
            "regra": "90% da altura x 2",
        },
        "emenda_corrente": {
            "quantidade_un": round(componentes.get("Emenda corrente", {}).quantidade, 4) if "Emenda corrente" in componentes else 0,
        },
        "pendulo": {
            "quantidade_un": round(componentes.get("Pêndulo", {}).quantidade, 4) if "Pêndulo" in componentes else 0,
        },
        "eixo_base": {
            "quantidade_ml": round(componentes.get("Eixo Base", {}).quantidade, 4) if "Eixo Base" in componentes else 0,
        },
        "base_cunha": {
            "quantidade_ml": round(componentes.get("Base Cunha", {}).quantidade, 4) if "Base Cunha" in componentes else 0,
        },
        "tampa_eixo": {
            "quantidade_un": round(componentes.get("Tampa Redonda do Eixo", {}).quantidade, 4) if "Tampa Redonda do Eixo" in componentes else 0,
        },
        "tampa_base": {
            "quantidade_un": round(componentes.get("Tampa Base", {}).quantidade, 4) if "Tampa Base" in componentes else 0,
        },
        "clips": {
            "quantidade_un": qtd_clips,
            "regra": "Até 1m = 2; depois +1 a cada 50cm",
        },
        "espaguete": {
            "quantidade_ml": round(componentes.get("Espaguete", {}).quantidade, 4) if "Espaguete" in componentes else 0,
        },
        "fita_plastica": {
            "quantidade_ml": round(componentes.get("Fita Plástica", {}).quantidade, 4) if "Fita Plástica" in componentes else 0,
        },
        "tampa_bando": {
            "quantidade_un": round(componentes.get("Tampa Bandô", {}).quantidade, 4) if "Tampa Bandô" in componentes else 0,
        } if com_bando else None,
    }


def simular_double_vision(produto, entrada: DoubleVisionSimulacaoInput) -> dict:
    """Executa a simulação técnica do Double Vision.

    Retorna erro 422 (ValueError) para combinação técnica inválida.
    """
    tipo = _tipo_double_vision(produto)
    if tipo != 'MANUAL':
        raise ValueError('Simulação disponível somente para produto final Double Vision manual.')

    # Seleção técnica do tubo pela regra central
    try:
        selecao = selecionar_tubo_double_vision(
            entrada.largura,
            tem_validacao_tecido_fornecedor=entrada.tem_validacao_tecido_fornecedor,
        )
    except LarguraExcedidaErro as exc:
        raise ValueError(str(exc)) from exc
    except LarguraInvalidaErro as exc:
        raise ValueError(str(exc)) from exc

    # Motor de cálculo de produção (custo técnico)
    catalogo = _montar_catalogo_double_vision(selecao.diametro, entrada.com_bando)
    # Remove None entries
    catalogo = {k: v for k, v in catalogo.items() if v is not None}

    opcoes = {
        "perda_tecido_percentual": 5.0,
        "desconto_largura_tubo_base": 0.025,
        "desconto_largura_tecido": 0.025,
        "sobra_altura_tecido": 0.15,
    }
    fabricacao = calcular_produto_sob_medida(
        "Double Vision",
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
    if custo is None:
        avisos.append('Sem custo cadastrado: preço comercial segue regra do backend sem novo acréscimo.')
    if preco <= 0:
        avisos.append('Preço indisponível: cadastro sem custo ou valor de venda positivo. Revise antes de salvar.')

    # Alertas técnicos específicos do Double Vision
    if selecao.estado == EstadoValidacao.REQUER_VALIDACAO:
        avisos.append(f'VALIDAÇÃO OBRIGATÓRIA: {selecao.motivo_bloqueio}')
    if selecao.estado == EstadoValidacao.BLOQUEADO:
        avisos.append(f'BLOQUEADO: {selecao.motivo_bloqueio}')

    componentes_tecnicos = _extrair_componentes_double_vision(fabricacao, selecao.diametro, entrada.com_bando, entrada.largura)

    return dict(
        modelo='DOUBLE VISION',
        quantidade_pecas=entrada.quantidade,
        area_real_m2=area_faturavel.area_real_m2,
        area_faturavel_m2=area_faturavel.area_faturavel_m2,
        minimo_faturavel_aplicado=area_faturavel.minimo_faturavel_aplicado,
        bitola_tecnica=selecao.diametro.value,
        estado_validacao=selecao.estado.value,
        requer_validacao_tecido_fornecedor=selecao.requer_validacao_tecido_fornecedor,
        permitido=selecao.permitido,
        motivo_bloqueio=selecao.motivo_bloqueio,
        largura_maxima_padrao_m=selecao.largura_maxima_padrao_m,
        largura_maxima_excepcional_m=selecao.largura_maxima_excepcional_m,
        fabricacao_por_peca=asdict(fabricacao),
        componentes_tecnicos=componentes_tecnicos,
        custo_tecnico=round(float(fabricacao.custo_total), 4) if fabricacao.custo_total > 0 else None,
        custo_cadastrado=float(custo) if custo is not None else None,
        preco_unitario=preco,
        subtotal=subtotal,
        preco_disponivel=preco > 0,
        alertas=avisos,
        origem_preco='CUSTO_CADASTRADO' if custo is not None else 'VALOR_VENDA_CADASTRADO',
        aviso='Simulação técnica recalculada por peça; não representa histórico nem composição integral precificada. Custo técnico só disponível quando componentes/equivalências válidas existirem no catálogo.',
    )