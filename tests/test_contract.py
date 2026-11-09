"""Teste de contrato: respostas reais x YAML, e rotas do código x YAML."""
from openapi_spec_validator import validate as validate_openapi

from tests.contract_utils import load_spec, response_schema, validate

SPEC = load_spec()


def _check(path, method, status, body):
    validate(SPEC, response_schema(SPEC, path, method, status), body)


def test_yaml_is_a_valid_openapi_document():
    validate_openapi(SPEC)


def test_success_responses_match_schemas(client):
    _check("/health", "get", "200", client.get("/health").json())
    _check("/points", "get", "200", client.get("/points").json())
    _check("/points/{point_id}", "get", "200", client.get("/points/P-002").json())
    ask = client.post("/ask", json={"question": "Como está o ponto P-002?"}).json()
    _check("/ask", "post", "200", ask)
    refusal = client.post("/ask", json={"question": "Qual é a capital da França?"}).json()
    _check("/ask", "post", "200", refusal)
    _check("/metrics", "get", "200", client.get("/metrics").json())


def test_error_responses_match_error_schema(client):
    cases = [
        (client.get("/points/P-999"), "/points/{point_id}", "get", "404", 404),
        (client.get("/points", params={"limit": 0}), "/points", "get", "400", 400),
        (client.post("/ask", json={}), "/ask", "post", "422", 422),
        (client.post("/ask", json={"question": "x", "point_id": "P-999"}),
         "/ask", "post", "404", 404),
    ]
    for response, path, method, status, expected in cases:
        assert response.status_code == expected
        _check(path, method, status, response.json())


def _declared_codes(operation):
    codes = set()
    for code, response in operation["responses"].items():
        schema = response.get("content", {}).get("application/json", {}).get("schema", {})
        if code == "422" and schema.get("$ref", "").endswith("HTTPValidationError"):
            continue  # 422 automático do FastAPI, mapeado para 400 pelo handler
        codes.add(code)
    return codes


def test_code_routes_and_status_codes_match_yaml(client):
    generated = client.get("/openapi.json").json()["paths"]
    assert set(generated) == set(SPEC["paths"])
    for path, methods in SPEC["paths"].items():
        assert set(generated[path]) == set(methods), path
        for method, operation in methods.items():
            assert _declared_codes(generated[path][method]) == set(operation["responses"]), (
                f"{method.upper()} {path}"
            )
