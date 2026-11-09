"""Schemas HTTP. Devem espelhar contract/openapi.yaml."""
from typing import Optional

from pydantic import BaseModel, Field

from src.domain.models import PointStatus, RefusalReason


class PointOut(BaseModel):
    id: str
    name: str
    line: str
    neighborhood: str
    status: PointStatus
    status_updated_at: str
    alternative_point_id: Optional[str] = None
    note: Optional[str] = None


class PointPage(BaseModel):
    items: list[PointOut]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    point_id: Optional[str] = Field(default=None, pattern=r"^P-\d{3}$")


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: Optional[RefusalReason] = None
    sources: list[str]
    model: Optional[str] = None


class HealthOut(BaseModel):
    status: str
    llm_provider: str


class MetricsOut(BaseModel):
    requests_total: int
    errors_5xx_total: int
    error_rate: float
    latency_p95_ms: float
    asks_total: int
    refusals_total: int
    refusal_rate: float
    llm_failures_total: int
    tokens_in_total: int
    tokens_out_total: int


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None
