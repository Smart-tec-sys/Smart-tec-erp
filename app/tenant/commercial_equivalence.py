"""Contrato futuro de equivalência, separado do núcleo técnico global."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommercialTechnicalEquivalence:
    empresa_id: int
    technical_function_code: str
    commercial_product_id: int
    supplier_id: int | None = None
    approved: bool = False

    def __post_init__(self) -> None:
        if self.empresa_id <= 0 or self.commercial_product_id <= 0:
            raise ValueError("empresa e produto devem ser positivos")
        if not self.technical_function_code.strip():
            raise ValueError("função técnica é obrigatória")
