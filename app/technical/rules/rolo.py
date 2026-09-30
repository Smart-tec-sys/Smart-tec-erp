"""Regra técnica central para seleção de tubo Rolô.

Regra confirmada (CONFIRMACAO_TECNICA_MANUAL):
- largura <= 1,80 m: tubo 32 mm, manual permitido
- largura > 1,80 m e <= 2,50 m: tubo 38 mm, manual permitido
- largura > 2,50 m e <= 3,20 m: tubo 43 mm, manual permitido
- largura > 3,20 m: manual proibido, motorização obrigatória,
  sugestão inicial 65 mm, requer confirmação do vendedor
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TuboRoloDiametro(str, Enum):
    D32 = "32mm"
    D38 = "38mm"
    D43 = "43mm"
    D65 = "65mm"
    D70 = "70mm"


class AcionamentoPermitido(str, Enum):
    MANUAL = "manual"
    MOTORIZADO = "motorizado"


@dataclass(frozen=True)
class TuboRoloSelecao:
    diametro: TuboRoloDiametro
    acionamento_permitido: AcionamentoPermitido
    requer_confirmacao_vendedor: bool = False
    observacao: str | None = None


class MotorObrigatorioErro(Exception):
    """Lançado quando a largura exige motorização e a seleção é manual."""

    def __init__(self, largura: float, diametro_sugerido: TuboRoloDiametro):
        self.largura = largura
        self.diametro_sugerido = diametro_sugerido
        super().__init__(
            f"Largura {largura:.2f}m excede 3,20m: manual proibido. "
            f"Motorização obrigatória. Diâmetro sugerido: {diametro_sugerido.value}. "
            f"Requer confirmação do vendedor."
        )


def selecionar_tubo_rolo(
    largura: float,
    acionamento: Literal["manual", "motorizado"] = "manual",
) -> TuboRoloSelecao:
    """
    Seleciona o tubo Rolô conforme regra técnica central.

    Args:
        largura: Largura em metros.
        acionamento: "manual" ou "motorizado".

    Returns:
        TuboRoloSelecao com diâmetro, acionamento permitido e flags.

    Raises:
        MotorObrigatorioErro: Se largura > 3,20m e acionamento for manual.
        ValueError: Se largura <= 0.
    """
    if largura <= 0:
        raise ValueError("Largura deve ser maior que zero")

    if largura <= 1.80:
        return TuboRoloSelecao(
            diametro=TuboRoloDiametro.D32,
            acionamento_permitido=AcionamentoPermitido.MANUAL,
        )

    if largura <= 2.50:
        return TuboRoloSelecao(
            diametro=TuboRoloDiametro.D38,
            acionamento_permitido=AcionamentoPermitido.MANUAL,
        )

    if largura <= 3.20:
        return TuboRoloSelecao(
            diametro=TuboRoloDiametro.D43,
            acionamento_permitido=AcionamentoPermitido.MANUAL,
        )

    # largura > 3.20
    if acionamento == "manual":
        raise MotorObrigatorioErro(largura, TuboRoloDiametro.D65)

    return TuboRoloSelecao(
        diametro=TuboRoloDiametro.D65,
        acionamento_permitido=AcionamentoPermitido.MOTORIZADO,
        requer_confirmacao_vendedor=True,
        observacao=(
            "Largura > 3,20m: motorização obrigatória. "
            "Sugestão inicial 65mm. Requer confirmação do vendedor. "
            "Situações especiais (ex.: pé-direito) podem usar 70mm ou outra solução validada."
        ),
    )


def tubo_para_codigo_tecnico(diametro: TuboRoloDiametro) -> str:
    """Converte diâmetro para código técnico do catálogo."""
    return f"TUBO_ROLO_{diametro.value.replace('mm', 'MM')}"


def codigo_tecnico_para_tubo(codigo: str) -> TuboRoloDiametro | None:
    """Converte código técnico para diâmetro, se conhecido."""
    codigo = codigo.strip().upper()
    mapping = {
        "TUBO_ROLO_32MM": TuboRoloDiametro.D32,
        "TUBO_ROLO_38MM": TuboRoloDiametro.D38,
        "TUBO_ROLO_43MM": TuboRoloDiametro.D43,
        "TUBO_ROLO_65MM": TuboRoloDiametro.D65,
        "TUBO_ROLO_70MM": TuboRoloDiametro.D70,
    }
    return mapping.get(codigo)