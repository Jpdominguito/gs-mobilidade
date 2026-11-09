"""Configuração por variáveis de ambiente. Nenhuma chave fica no código."""
import os
from dataclasses import dataclass
from pathlib import Path

from src.infra.llm_fake import FakeLlm
from src.infra.llm_ollama import OllamaLlm

DEFAULT_DATA = Path(__file__).parent / "data" / "points.json"


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "fake"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    data_path: Path = DEFAULT_DATA

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "fake").lower(),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            data_path=Path(os.getenv("POINTS_DATA_PATH", str(DEFAULT_DATA))),
        )


def build_llm(settings: Settings):
    """Único lugar que conhece os modelos. Trocar de LLM = mudar LLM_PROVIDER."""
    if settings.llm_provider == "fake":
        return FakeLlm()
    if settings.llm_provider == "ollama":
        return OllamaLlm(settings.ollama_url, settings.ollama_model)
    raise ValueError(f"LLM_PROVIDER desconhecido: {settings.llm_provider}")
