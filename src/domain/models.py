"""Modelos do domínio de mobilidade. Sem dependência de framework ou de LLM."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PointStatus(str, Enum):
    OPERATING = "OPERATING"
    DELAYED = "DELAYED"
    INTERRUPTED = "INTERRUPTED"


class RefusalReason(str, Enum):
    NO_DATA = "NO_DATA"
    UNSAFE_INPUT = "UNSAFE_INPUT"
    UNVERIFIED_ANSWER = "UNVERIFIED_ANSWER"


@dataclass(frozen=True)
class Point:
    id: str
    name: str
    line: str
    neighborhood: str
    status: PointStatus
    status_updated_at: str
    alternative_point_id: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class Page:
    items: list
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class LlmRequest:
    system: str
    prompt: str


@dataclass(frozen=True)
class LlmResponse:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class Answer:
    text: str
    refused: bool
    refusal_reason: Optional[RefusalReason] = None
    sources: list = field(default_factory=list)
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
