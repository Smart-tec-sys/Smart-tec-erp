"""Regras técnicas centrais do núcleo SmartTec."""

from .rolo import (
    selecionar_tubo_rolo,
    TuboRoloSelecao,
    MotorObrigatorioErro,
)
from .double_vision import (
    selecionar_tubo_double_vision,
    TuboDVSelecao,
    TuboDVdiametro,
    EstadoValidacao,
    LarguraInvalidaErro,
    LarguraExcedidaErro,
    tubo_para_codigo_tecnico as dv_tubo_para_codigo_tecnico,
    codigo_tecnico_para_tubo as dv_codigo_tecnico_para_tubo,
    validar_largura_double_vision,
    obter_limites_double_vision,
)

__all__ = [
    "selecionar_tubo_rolo",
    "TuboRoloSelecao",
    "MotorObrigatorioErro",
    "selecionar_tubo_double_vision",
    "TuboDVSelecao",
    "TuboDVdiametro",
    "EstadoValidacao",
    "LarguraInvalidaErro",
    "LarguraExcedidaErro",
    "dv_tubo_para_codigo_tecnico",
    "dv_codigo_tecnico_para_tubo",
    "validar_largura_double_vision",
    "obter_limites_double_vision",
]