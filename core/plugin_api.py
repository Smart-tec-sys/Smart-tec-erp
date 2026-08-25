from abc import ABC, abstractmethod


class FrontPlugin(ABC):
    slug: str
    label: str
    group: str | None

    @abstractmethod
    def render(self): ...


class BackPlugin(ABC):

    @abstractmethod
    def register(self, app): ...
