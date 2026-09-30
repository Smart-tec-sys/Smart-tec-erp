"""Regra central de área faturável para produtos vendidos em M².

Apenas define o mínimo de cobrança (1,50 m²). Não altera cálculo técnico/fabricação.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MINIMO_FATURAVEL_M2 = Decimal("1.50")


@dataclass
class AreaFaturavelResultado:
    area_real_m2: Decimal
    area_faturavel_m2: Decimal
    minimo_faturavel_aplicado: bool


def _normalizar_unidade(unidade: str | None) -> str:
    """Normaliza a unidade de venda para comparação."""
    if not unidade:
        return ""
    return "".join(c for c in unidade.upper() if c.isalnum())


def _unidade_eh_m2(unidade: str | None) -> bool:
    """Verifica se a unidade de venda é M² (metro quadrado)."""
    normalizada = _normalizar_unidade(unidade)
    return normalizada in ("M2", "M²", "M2", "METROQUADRADO", "MQ")


def calcular_area_faturavel(
    largura: float,
    altura: float,
    quantidade: int,
    unidade_venda: str | None,
) -> AreaFaturavelResultado:
    """
    Calcula a área real e a área faturável aplicando o mínimo de 1,50 m²
    apenas para produtos vendidos em M².

    Args:
        largura: Largura em metros
        altura: Altura em metros
        quantidade: Quantidade de peças
        unidade_venda: Unidade de venda do produto (ex: "M²", "UN", "KIT", "ML", "PAR")

    Returns:
        AreaFaturavelResultado com:
        - area_real_m2: largura * altura * quantidade (sem mínimo)
        - area_faturavel_m2: max(area_real_m2, 1.50) * quantidade se M², senão area_real_m2
        - minimo_faturavel_aplicado: True se o mínimo foi aplicado
    """
    largura_d = Decimal(str(largura))
    altura_d = Decimal(str(altura))
    qtd_d = Decimal(str(quantidade))

    area_real_por_peca = (largura_d * altura_d).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    area_real_total = (area_real_por_peca * qtd_d).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    if _unidade_eh_m2(unidade_venda):
        area_faturavel_por_peca = max(area_real_por_peca, MINIMO_FATURAVEL_M2)
        minimo_aplicado = area_real_por_peca < MINIMO_FATURAVEL_M2
        area_faturavel_total = (area_faturavel_por_peca * qtd_d).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        area_faturavel_total = area_real_total
        minimo_aplicado = False

    return AreaFaturavelResultado(
        area_real_m2=area_real_total,
        area_faturavel_m2=area_faturavel_total,
        minimo_faturavel_aplicado=minimo_aplicado,
    )