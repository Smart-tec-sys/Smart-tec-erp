"""Motor geométrico puro para a Romana padrão manual.

Este módulo não consulta banco, não calcula preço e não estima materiais.
"""

from dataclasses import dataclass, field
from math import floor


STATUS_CALCULO = "CALCULO_GEOMETRICO_CONCLUIDO"
STATUS_PENDENTE = "PENDENTE_CONFIRMACAO"
TIPO_SUPORTADO = "ROMANA"
ACIONAMENTO_SUPORTADO = "MANUAL"


@dataclass(frozen=True)
class RomanaCalculoEntrada:
    largura_cm: float
    altura_cm: float
    quantidade: int
    tipo: str = TIPO_SUPORTADO
    acionamento: str = ACIONAMENTO_SUPORTADO


@dataclass(frozen=True)
class RomanaCalculoResultado:
    largura_cm: float
    altura_cm: float
    quantidade: int
    quantidade_gomos: int
    quantidade_gomos_inteiros: int
    tamanho_gomo_cm: float
    tamanho_base_cm: float
    alertas: tuple[str, ...] = field(default_factory=tuple)
    status_calculo: str = STATUS_CALCULO
    regra_varetas_status: str = STATUS_PENDENTE
    calculo_tecido_producao: str = "PENDENTE"
    cabeceira_referencia_cm: float | None = None
    base_referencia_cm: float | None = None
    cordoes_carreteis_comando_status: str = STATUS_PENDENTE


def _arredondar_comercial_positivo(valor: float) -> int:
    """Arredonda valor positivo para o inteiro mais próximo, com 0,5 para cima."""
    return floor(valor + 0.5)


def calcular_producao_romana(
    entrada: RomanaCalculoEntrada,
) -> RomanaCalculoResultado:
    """Calcula somente a geometria dos gomos da Romana padrão manual V1."""
    if entrada.largura_cm <= 0:
        raise ValueError("largura_cm deve ser maior que zero")
    if entrada.altura_cm <= 0:
        raise ValueError("altura_cm deve ser maior que zero")
    if entrada.quantidade <= 0:
        raise ValueError("quantidade deve ser maior que zero")
    if entrada.tipo.upper() != TIPO_SUPORTADO:
        raise ValueError("somente o tipo ROMANA possui regra produtiva V1")
    if entrada.acionamento.upper() != ACIONAMENTO_SUPORTADO:
        raise ValueError("somente o acionamento MANUAL possui regra produtiva V1")

    quantidade_gomos = max(1, _arredondar_comercial_positivo(entrada.altura_cm / 25))
    tamanho_gomo_cm = entrada.altura_cm / (quantidade_gomos - 0.5)
    tamanho_base_cm = tamanho_gomo_cm / 2

    return RomanaCalculoResultado(
        largura_cm=float(entrada.largura_cm),
        altura_cm=float(entrada.altura_cm),
        quantidade=int(entrada.quantidade),
        quantidade_gomos=quantidade_gomos,
        quantidade_gomos_inteiros=max(0, quantidade_gomos - 1),
        tamanho_gomo_cm=tamanho_gomo_cm,
        tamanho_base_cm=tamanho_base_cm,
        alertas=(
            "Altura informada representa a altura pronta; consumo de tecido pendente.",
            "Varetas, cordões, carretéis e comando dependem de confirmação da produção.",
        ),
        cabeceira_referencia_cm=float(entrada.largura_cm),
        base_referencia_cm=float(entrada.largura_cm),
    )

