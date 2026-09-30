"""Unidades de fabricação, independentes das unidades comerciais."""

from enum import Enum


class TechnicalUnit(str, Enum):
    UN = "UN"
    M = "M"
    M2 = "M2"
    CJ = "CJ"
    KIT = "KIT"


VALID_TECHNICAL_UNITS = frozenset(TechnicalUnit)
