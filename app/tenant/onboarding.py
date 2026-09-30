"""Preview puro de onboarding; não cria empresa ou dados comerciais."""

from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Any, Mapping

from app.technical.catalog import TECHNICAL_CATALOG


@dataclass(frozen=True)
class TenantOnboardingInput:
    nome: str
    slug: str
    documento: str | None = None
    configuracoes_iniciais: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ValueError("nome é obrigatório")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValueError("slug inválido")
        object.__setattr__(
            self, "configuracoes_iniciais",
            MappingProxyType(dict(self.configuracoes_iniciais)),
        )


@dataclass(frozen=True)
class TenantOnboardingPreview:
    entrada: TenantOnboardingInput
    portfolio: tuple[str, ...] = ()
    produtos: tuple = ()
    fornecedores: tuple = ()
    clientes: tuple = ()
    orcamentos: tuple = ()
    estoque: tuple = ()
    custos: tuple = ()
    funcoes_tecnicas_globais: tuple[str, ...] = ()


def preview_zero_tenant(entrada: TenantOnboardingInput) -> TenantOnboardingPreview:
    return TenantOnboardingPreview(
        entrada=entrada,
        funcoes_tecnicas_globais=tuple(TECHNICAL_CATALOG),
    )
