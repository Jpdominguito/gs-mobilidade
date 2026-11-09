"""Testes da camada HTTP com TestClient e LLM fake."""
from src.infra.llm_fake import FakeLlm


def test_get_point_200(client):  # caminho feliz
    response = client.get("/points/P-003")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INTERRUPTED"
    assert body["alternative_point_id"] == "P-004"
    assert "X-Request-ID" in response.headers


def test_get_point_404_uses_standard_error_body(client):  # caminho de erro
    response = client.get("/points/P-999")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "POINT_NOT_FOUND"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_list_points_paginates_and_filters(client):
    first = client.get("/points", params={"limit": 4, "offset": 0}).json()
    assert len(first["items"]) == 4
    assert first["total"] == 9
    assert first["next_offset"] == 4
    last = client.get("/points", params={"limit": 4, "offset": 8}).json()
    assert len(last["items"]) == 1
    assert last["next_offset"] is None
    delayed = client.get("/points", params={"status": "DELAYED"}).json()
    assert {p["id"] for p in delayed["items"]} == {"P-002", "P-006"}


def test_list_points_invalid_query_returns_400(client):
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "BROKEN"}):
        response = client.get("/points", params=params)
        assert response.status_code == 400, params
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_ask_200_with_fake_llm(client):
    response = client.post("/ask", json={"question": "Como está o ponto P-003?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["sources"] == ["P-003"]
    assert "interrompido" in body["answer"]


def test_ask_refusal_is_200_with_reason(client):
    response = client.post("/ask", json={"question": "Qual é a capital da França?"})
    assert response.status_code == 200
    assert response.json()["refusal_reason"] == "NO_DATA"


def test_ask_unknown_point_id_returns_404(client):
    response = client.post("/ask", json={"question": "Como está?", "point_id": "P-999"})
    assert response.status_code == 404


def test_ask_422_for_personal_data_and_bad_schema(client):
    pii = client.post("/ask", json={"question": "meu email é ana@exemplo.com, P-001?"})
    assert pii.status_code == 422
    assert pii.json()["code"] == "INVALID_QUESTION"
    missing = client.post("/ask", json={})
    assert missing.status_code == 422
    assert missing.json()["code"] == "VALIDATION_ERROR"


def test_ask_malformed_json_returns_400(client):
    response = client.post(
        "/ask", content="{nao é json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400


def test_ask_503_when_llm_is_down(make_client):
    client = make_client(FakeLlm(fail=True))
    response = client.post("/ask", json={"question": "Como está o ponto P-001?"})
    assert response.status_code == 503
    assert response.json()["code"] == "LLM_UNAVAILABLE"
    assert client.get("/points/P-001").status_code == 200  # o resto segue de pé


def test_metrics_reflect_traffic(client):
    client.get("/points/P-001")
    client.post("/ask", json={"question": "Qual é a capital da França?"})
    metrics = client.get("/metrics").json()
    assert metrics["requests_total"] >= 2
    assert metrics["asks_total"] == 1
    assert metrics["refusals_total"] == 1
    assert metrics["refusal_rate"] == 1.0
