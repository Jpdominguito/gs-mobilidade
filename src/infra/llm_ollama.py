"""Adaptador do Ollama (local ou cloud) usando apenas a biblioteca padrão."""
import json
import urllib.request

from src.domain.errors import LlmUnavailable
from src.domain.models import LlmRequest, LlmResponse


class OllamaLlm:
    def __init__(self, base_url: str, model: str, timeout_s: float = 20.0):
        self._url = base_url.rstrip("/") + "/api/generate"
        self._model = model
        self._timeout = timeout_s

    def generate(self, request: LlmRequest) -> LlmResponse:
        payload = {
            "model": self._model,
            "system": request.system,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        http_request = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError) as exc:  # URLError, timeout e JSON inválido
            raise LlmUnavailable(f"Falha ao chamar o Ollama: {exc}") from exc
        text = str(data.get("response", "")).strip()
        if not text:
            raise LlmUnavailable("O Ollama retornou resposta vazia.")
        return LlmResponse(
            text=text,
            model=self._model,
            tokens_in=int(data.get("prompt_eval_count", 0)),
            tokens_out=int(data.get("eval_count", 0)),
        )
