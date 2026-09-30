"""Regra técnica central para seleção de tubo Double Vision manual.

Regra confirmada (CONFIRMACAO_TECNICA_MANUAL):
- largura <= 1,80 m: tubo 32 mm
- largura > 1,80 m e <= 2,80 m: tubo 38 mm
- largura máxima padrão: 2,60 m
- largura máxima excepcional: 2,80 m (requer validação explícita de tecido/fornecedor)
- acima de 2,80 m: bloqueado
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TuboDVdiametro(str, Enum):
    D32 = "32mm"
    D38 = "38mm"


class EstadoValidacao(str, Enum):
    PERMITIDO = "permitido"
    REQUER_VALIDACAO = "requer_validacao"
    BLOQUEADO = "bloqueado"


@dataclass(frozen=True)
class TuboDVSelecao:
    diametro: TuboDVdiametro | None
    largura_maxima_padrao_m: float
    largura_maxima_excepcional_m: float
    estado: EstadoValidacao
    requer_validacao_tecido_fornecedor: bool
    permitido: bool
    motivo_bloqueio: str | None
    origem: str


class LarguraInvalidaErro(Exception):
    """Lançado quando a largura é inválida (<= 0)."""

    def __init__(self, largura: float):
        self.largura = largura
        super().__init__(f"Largura deve ser maior que zero: {largura}")


class LarguraExcedidaErro(Exception):
    """Lançado quando a largura excede o máximo absoluto (2,80 m)."""

    def __init__(self, largura: float):
        self.largura = largura
        super().__init__(
            f"Largura {largura:.2f}m excede o máximo absoluto de 2,80m para Double Vision. "
            f"Não é possível fabricar."
        )


def selecionar_tubo_double_vision(
    largura: float,
    *,
    tem_validacao_tecido_fornecedor: bool = False,
) -> TuboDVSelecao:
    """
    Seleciona o tubo Double Vision manual conforme regra técnica central.

    Args:
        largura: Largura em metros.
        tem_validacao_tecido_fornecedor: True se houver evidência explícita
            de compatibilidade do tecido/fornecedor para larguras > 2,60m.

    Returns:
        TuboDVSelecao com diâmetro, limites, estado de validação e flags.

    Raises:
        LarguraInvalidaErro: Se largura <= 0.
        LarguraExcedidaErro: Se largura > 2,80m.
    """
    if largura <= 0:
        raise LarguraInvalidaErro(largura)

    ORIGEM = "CONFIRMACAO_TECNICA_MANUAL"
    LARGURA_MAX_PADRAO = 2.60
    LARGURA_MAX_EXCEPCIONAL = 2.80

    if largura <= 1.80:
        return TuboDVSelecao(
            diametro=TuboDVdiametro.D32,
            largura_maxima_padrao_m=LARGURA_MAX_PADRAO,
            largura_maxima_excepcional_m=LARGURA_MAX_EXCEPCIONAL,
            estado=EstadoValidacao.PERMITIDO,
            requer_validacao_tecido_fornecedor=False,
            permitido=True,
            motivo_bloqueio=None,
            origem=ORIGEM,
        )

    if largura <= LARGURA_MAX_PADRAO:
        return TuboDVSelecao(
            diametro=TuboDVdiametro.D38,
            largura_maxima_padrao_m=LARGURA_MAX_PADRAO,
            largura_maxima_excepcional_m=LARGURA_MAX_EXCEPCIONAL,
            estado=EstadoValidacao.PERMITIDO,
            requer_validacao_tecido_fornecedor=False,
            permitido=True,
            motivo_bloqueio=None,
            origem=ORIGEM,
        )

    if largura <= LARGURA_MAX_EXCEPCIONAL:
        if tem_validacao_tecido_fornecedor:
            return TuboDVSelecao(
                diametro=TuboDVdiametro.D38,
                largura_maxima_padrao_m=LARGURA_MAX_PADRAO,
                largura_maxima_excepcional_m=LARGURA_MAX_EXCEPCIONAL,
                estado=EstadoValidacao.PERMITIDO,
                requer_validacao_tecido_fornecedor=True,
                permitido=True,
                motivo_bloqueio=None,
                origem=ORIGEM,
            )
        return TuboDVSelecao(
            diametro=TuboDVdiametro.D38,
            largura_maxima_padrao_m=LARGURA_MAX_PADRAO,
            largura_maxima_excepcional_m=LARGURA_MAX_EXCEPCIONAL,
            estado=EstadoValidacao.REQUER_VALIDACAO,
            requer_validacao_tecido_fornecedor=True,
            permitido=False,
            motivo_bloqueio=(
                f"Largura {largura:.2f}m excede o padrão de 2,60m. "
                f"Requer validação explícita de compatibilidade do tecido/fornecedor "
                f"para até 2,80m."
            ),
            origem=ORIGEM,
        )

    raise LarguraExcedidaErro(largura)


def tubo_para_codigo_tecnico(diametro: TuboDVdiametro) -> str:
    """Converte diâmetro para código técnico do catálogo."""
    return f"TUBO_DOUBLE_VISION_{diametro.value.replace('mm', 'MM')}"


def codigo_tecnico_para_tubo(codigo: str) -> TuboDVdiametro | None:
    """Converte código técnico para diâmetro, se conhecido."""
    codigo = codigo.strip().upper()
    mapping = {
        "TUBO_DOUBLE_VISION_32MM": TuboDVdiametro.D32,
        "TUBO_DOUBLE_VISION_38MM": TuboDVdiametro.D38,
    }
    return mapping.get(codigo)


def validar_largura_double_vision(largura: float) -> tuple[bool, str | None]:
    """
    Validação rápida de largura para uso em UI/orçamentos.

    Returns:
        Tupla (permitido, motivo_bloqueio). Se permitido=True, motivo_bloqueio é None.
    """
    try:
        selecao = selecionar_tubo_double_vision(largura)
        return selecao.permitido, selecao.motivo_bloqueio
    except LarguraExcedidaErro as e:
        return False, str(e)
    except LarguraInvalidaErro as e:
        return False, str(e)


def obter_limites_double_vision() -> dict:
    """Retorna os limites técnicos para documentação/UI."""
    return {
        "limite_tubo_32mm_m": 1.80,
        "limite_tubo_38mm_m": 2.80,
        "largura_maxima_padrao_m": 2.60,
        "largura_maxima_excepcional_m": 2.80,
        "largura_maxima_absoluta_m": 2.80,
        "requer_validacao_acima_de_m": 2.60,
        "origem": "CONFIRMACAO_TECNICA_MANUAL",
    }