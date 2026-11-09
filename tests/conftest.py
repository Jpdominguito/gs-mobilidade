import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.domain.services import AskService, PointService
from src.infra.config import DEFAULT_DATA
from src.infra.llm_fake import FakeLlm
from src.infra.observability import Metrics
from src.infra.repository_json import JsonPointRepository


@pytest.fixture
def repository():
    return JsonPointRepository(DEFAULT_DATA)


@pytest.fixture
def make_client(repository):
    """Fábrica de clientes HTTP com o LLM injetado (sempre fake nos testes)."""

    def _make(llm=None) -> TestClient:
        llm = llm or FakeLlm()
        app = create_app(
            PointService(repository), AskService(repository, llm), Metrics(), "fake"
        )
        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client):
    return make_client()
