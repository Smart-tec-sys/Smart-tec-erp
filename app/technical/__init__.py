"""Núcleo técnico universal, independente do catálogo comercial."""

from .catalog import TECHNICAL_CATALOG, get_technical_function
from .models import TechnicalFunction, TechnicalFunctionStatus, TechnicalRequirement
from .units import TechnicalUnit

__all__ = [
    "TECHNICAL_CATALOG", "TechnicalFunction", "TechnicalFunctionStatus",
    "TechnicalRequirement", "TechnicalUnit", "get_technical_function",
]
