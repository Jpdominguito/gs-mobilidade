"""LLM falso e determinístico. Usado nos testes e como modo local sem modelo."""
import re
from typing import Optional

from src.domain.errors import LlmUnavailable
from src.domain.models import LlmRequest, LlmResponse

_STATUS_TEXT = {
    "OPERATING": "operando normalmente",
    "DELAYED": "com atrasos",
    "INTERRUPTED": "interrompido",
}
_LINE = re.compile(r"\[(P-\d{3})\][^\n]*")


class FakeLlm:
    """Monta uma resposta a partir dos DADOS do prompt, sem rede e sem aleatoriedade."""

    def __init__(self, canned: Optional[str] = None, fail: bool = False):
        self._canned = canned
        self._fail = fail
        self.calls = 0

    def generate(self, request: LlmRequest) -> LlmResponse:
        self.calls += 1
        if self._fail:
            raise LlmUnavailable("Modelo indisponível (fake).")
        text = self._canned if self._canned is not None else self._from_prompt(request.prompt)
        return LlmResponse(
            text=text,
            model="fake-llm",
            tokens_in=len(request.prompt.split()),
            tokens_out=len(text.split()),
        )

    @staticmethod
    def _from_prompt(prompt: str) -> str:
        match = _LINE.search(prompt)
        if not match:
            return "Não tenho essa informação."
        line, point_id = match.group(0), match.group(1)
        name = re.search(r"nome=([^;]*)", line)
        status = re.search(r"status=([A-Z_]+)", line)
        alt = re.search(r"alternativa=(P-\d{3})", line)
        status_text = _STATUS_TEXT.get(status.group(1) if status else "", "sem status")
        text = f"O ponto {point_id} ({name.group(1) if name else '?'}) está {status_text}."
        if alt:
            text += f" Alternativa: ponto {alt.group(1)}."
        return text
