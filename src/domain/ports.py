"""Portas (interfaces) que o domínio exige da infraestrutura."""
from typing import Optional, Protocol

from src.domain.models import LlmRequest, LlmResponse, Page, Point, PointStatus


class PointRepository(Protocol):
    def get(self, point_id: str) -> Optional[Point]: ...

    def list_points(
        self, status: Optional[PointStatus], limit: int, offset: int
    ) -> Page: ...

    def all_points(self) -> "list[Point]": ...


class LlmPort(Protocol):
    """Qualquer modelo de linguagem entra por aqui.

    Deve levantar LlmUnavailable quando o modelo não puder responder.
    """

    def generate(self, request: LlmRequest) -> LlmResponse: ...
