"""Casos de uso. Dependem apenas das portas, nunca de uma biblioteca de LLM."""
import re
from typing import Optional

from src.domain.errors import PointNotFound
from src.domain.guardrails import is_injection, normalize, sanitize_question, verify_answer
from src.domain.models import (
    Answer,
    LlmRequest,
    Page,
    Point,
    PointStatus,
    RefusalReason,
)
from src.domain.ports import LlmPort, PointRepository

MAX_CONTEXT_POINTS = 3

SYSTEM_PROMPT = (
    "Você é o assistente de mobilidade urbana da prefeitura. "
    "Responda SOMENTE com base nos DADOS fornecidos. "
    "Se os dados não bastarem, diga que não tem a informação. "
    "Nunca peça nem repita dados pessoais. "
    "Responda em português, em até 3 frases, citando o código do ponto (ex.: P-001)."
)

REFUSAL_TEXTS = {
    RefusalReason.NO_DATA: (
        "Não encontrei informação sobre isso nos dados de mobilidade. "
        "Informe o código do ponto (ex.: P-001), a linha ou o bairro."
    ),
    RefusalReason.UNSAFE_INPUT: (
        "Não posso atender a esse tipo de pedido. "
        "Posso informar o status de pontos e linhas de ônibus."
    ),
    RefusalReason.UNVERIFIED_ANSWER: (
        "Não consegui confirmar essa resposta com os dados oficiais. "
        "Consulte o status do ponto diretamente pelo código."
    ),
}

_STOPWORDS = {
    "de", "da", "do", "das", "dos", "as", "os", "um", "uma", "que", "como", "esta",
    "estao", "qual", "quais", "onde", "ponto", "pontos", "onibus", "linha", "para",
    "com", "por", "tem", "ha", "na", "no", "nas", "nos", "em", "ou", "rua", "avenida",
    "av", "hoje", "agora", "status", "situacao", "alternativa", "funcionando",
}
_WORD = re.compile(r"[a-z0-9][a-z0-9\-]*")


class PointService:
    def __init__(self, repository: PointRepository):
        self._repo = repository

    def get_point(self, point_id: str) -> Point:
        point = self._repo.get(point_id)
        if point is None:
            raise PointNotFound(f"Ponto {point_id} não encontrado.")
        return point

    def list_points(self, status: Optional[PointStatus], limit: int, offset: int) -> Page:
        return self._repo.list_points(status, limit, offset)


def format_point_line(point: Point) -> str:
    return (
        f"[{point.id}] nome={point.name}; linha={point.line}; "
        f"bairro={point.neighborhood}; status={point.status.value}; "
        f"atualizado_em={point.status_updated_at}; "
        f"alternativa={point.alternative_point_id or 'nenhuma'}; "
        f"observacao={point.note or 'nenhuma'}"
    )


def build_prompt(question: str, points: "list[Point]") -> str:
    lines = "\n".join(format_point_line(p) for p in points)
    return f"DADOS:\n{lines}\n\nPERGUNTA: <pergunta>{question}</pergunta>"


def _refusal(reason: RefusalReason, **extra) -> Answer:
    return Answer(text=REFUSAL_TEXTS[reason], refused=True, refusal_reason=reason, **extra)


class AskService:
    def __init__(self, repository: PointRepository, llm: LlmPort):
        self._repo = repository
        self._llm = llm

    def ask(self, question: str, point_id: Optional[str] = None) -> Answer:
        clean = sanitize_question(question)  # levanta InvalidQuestion (G2)
        if is_injection(clean):
            return _refusal(RefusalReason.UNSAFE_INPUT)

        points = self._select_points(clean, point_id)
        if not points:
            return _refusal(RefusalReason.NO_DATA)  # sem contexto, o LLM nem é chamado

        response = self._llm.generate(
            LlmRequest(system=SYSTEM_PROMPT, prompt=build_prompt(clean, points))
        )
        sources = [p.id for p in points]
        allowed = set(sources) | {p.alternative_point_id for p in points if p.alternative_point_id}
        if not verify_answer(response.text, allowed):  # G1
            return _refusal(
                RefusalReason.UNVERIFIED_ANSWER,
                sources=sources,
                model=response.model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
        return Answer(
            text=response.text.strip(),
            refused=False,
            sources=sources,
            model=response.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

    def _select_points(self, clean_question: str, point_id: Optional[str]) -> "list[Point]":
        if point_id:
            point = self._repo.get(point_id)
            if point is None:
                raise PointNotFound(f"Ponto {point_id} não encontrado.")
            return [point]

        tokens = {t for t in _WORD.findall(normalize(clean_question))
                  if len(t) >= 3 and t not in _STOPWORDS}
        scored = []
        for point in self._repo.all_points():
            searchable = " ".join([point.id, point.name, point.line, point.neighborhood])
            words = set(_WORD.findall(normalize(searchable)))
            score = len(tokens & words)
            if score > 0:
                scored.append((-score, point.id, point))
        scored.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in scored[:MAX_CONTEXT_POINTS]]
