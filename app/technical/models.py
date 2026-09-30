"""Contratos puros e imutáveis do núcleo técnico SmartTec."""

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from .units import TechnicalUnit


class TechnicalFunctionStatus(str, Enum):
    ATIVA = "ATIVA"
    PROVISORIA = "PROVISORIA"
    PENDENTE_VALIDACAO = "PENDENTE_VALIDACAO"
    SEM_REGRA = "SEM_REGRA"


def _freeze_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True)
class TechnicalFunction:
    codigo: str
    nome: str
    familia: str
    unidade_tecnica: TechnicalUnit
    descricao: str
    atributos_requeridos: frozenset[str] = field(default_factory=frozenset)
    atributos_tecnicos: Mapping[str, Any] = field(default_factory=dict)
    ativo: bool = True
    versao: int = 1
    status: TechnicalFunctionStatus = TechnicalFunctionStatus.ATIVA
    grupo_alternativa: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", self.codigo.strip().upper())
        object.__setattr__(self, "familia", self.familia.strip().upper())
        object.__setattr__(self, "atributos_requeridos", frozenset(self.atributos_requeridos))
        object.__setattr__(self, "atributos_tecnicos", _freeze_mapping(self.atributos_tecnicos))
        if not self.codigo or not self.nome.strip() or not self.familia:
            raise ValueError("código, nome e família são obrigatórios")
        if not isinstance(self.unidade_tecnica, TechnicalUnit):
            raise ValueError("unidade técnica inválida")
        if not isinstance(self.status, TechnicalFunctionStatus):
            raise ValueError("status técnico inválido")
        if self.versao < 1:
            raise ValueError("versão deve ser maior ou igual a 1")


@dataclass(frozen=True)
class TechnicalRequirement:
    funcao_tecnica: str
    quantidade: float
    unidade: TechnicalUnit
    atributos: Mapping[str, Any] = field(default_factory=dict)
    origem_regra: str = ""
    obrigatorio: bool = True
    grupo_alternativa: str | None = None
    observacao_tecnica: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "funcao_tecnica", self.funcao_tecnica.strip().upper())
        object.__setattr__(self, "atributos", _freeze_mapping(self.atributos))
        if not self.funcao_tecnica:
            raise ValueError("função técnica é obrigatória")
        if not isinstance(self.unidade, TechnicalUnit):
            raise ValueError("unidade técnica inválida")
        if not isfinite(float(self.quantidade)) or self.quantidade < 0:
            raise ValueError("quantidade deve ser finita e não negativa")
