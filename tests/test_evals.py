"""Garante que o harness de evals continua válido. Usa o fake, nunca o LLM real."""
from evals.run_evals import load_cases, run
from src.domain.services import AskService
from src.infra.config import DEFAULT_DATA
from src.infra.llm_fake import FakeLlm
from src.infra.repository_json import JsonPointRepository


def test_eval_set_has_expected_size_and_edge_cases():
    cases = load_cases()
    assert len(cases) == 30
    categories = {c["category"] for c in cases}
    assert {"fora_de_escopo", "ponto_inexistente", "injecao", "dado_pessoal"} <= categories


def test_eval_harness_passes_all_cases_with_fake_llm():
    repository = JsonPointRepository(DEFAULT_DATA)
    result = run(load_cases(), AskService(repository, FakeLlm()))
    assert result["failures"] == []
    assert result["overall_rate"] == 1.0
    assert result["safety_rate"] == 1.0
