"""Testes do adaptador do Ollama com a rede substituída (sem LLM real)."""
import json
import urllib.error

import pytest

from src.domain.errors import LlmUnavailable
from src.domain.models import LlmRequest
from src.infra.config import Settings, build_llm
from src.infra.llm_fake import FakeLlm
from src.infra.llm_ollama import OllamaLlm


class _FakeHttpResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


REQUEST = LlmRequest(system="s", prompt="p")


def test_ollama_adapter_parses_response_and_tokens(monkeypatch):
    payload = {"response": " ok P-001 ", "prompt_eval_count": 12, "eval_count": 5}
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeHttpResponse(payload)
    )
    result = OllamaLlm("http://x", "m").generate(REQUEST)
    assert (result.text, result.tokens_in, result.tokens_out) == ("ok P-001", 12, 5)


def test_ollama_connection_error_becomes_llm_unavailable(monkeypatch):
    def boom(*args, **kwargs):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(LlmUnavailable):
        OllamaLlm("http://x", "m").generate(REQUEST)


def test_ollama_empty_response_becomes_llm_unavailable(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeHttpResponse({"response": "  "})
    )
    with pytest.raises(LlmUnavailable):
        OllamaLlm("http://x", "m").generate(REQUEST)


def test_build_llm_switches_provider_by_configuration():
    assert isinstance(build_llm(Settings(llm_provider="fake")), FakeLlm)
    assert isinstance(build_llm(Settings(llm_provider="ollama")), OllamaLlm)
    with pytest.raises(ValueError):
        build_llm(Settings(llm_provider="inexistente"))
