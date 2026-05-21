from dataclasses import dataclass
from typing import Callable


@dataclass
class KPI:
    label: str
    value_fn: Callable[[], str | int | float]  # função que devolve o valor em tempo real
    icon: str | None = None
    format: str = "{}"  # ex.: "R$ {:,.2f}"
