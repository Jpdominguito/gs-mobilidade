"""Validador mínimo de schemas OpenAPI 3.0 (sem dependências extras)."""
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).resolve().parent.parent / "contract" / "openapi.yaml"


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def resolve(spec: dict, schema: dict) -> dict:
    while "$ref" in schema:
        node = spec
        for part in schema["$ref"][2:].split("/"):
            node = node[part]
        schema = node
    return schema


def validate(spec: dict, schema: dict, value, path: str = "$") -> None:
    """Levanta AssertionError se `value` violar `schema`."""
    schema = resolve(spec, schema)
    if value is None:
        assert schema.get("nullable"), f"{path}: null não permitido pelo contrato"
        return
    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value!r} fora do enum {schema['enum']}"
    kind = schema.get("type")
    if kind == "object":
        assert isinstance(value, dict), f"{path}: esperado objeto"
        for name in schema.get("required", []):
            assert name in value, f"{path}: campo obrigatório ausente: {name}"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            assert not extra, f"{path}: campos fora do contrato: {sorted(extra)}"
        for name, item in value.items():
            if name in props:
                validate(spec, props[name], item, f"{path}.{name}")
    elif kind == "array":
        assert isinstance(value, list), f"{path}: esperado array"
        for index, item in enumerate(value):
            validate(spec, schema["items"], item, f"{path}[{index}]")
    elif kind == "string":
        assert isinstance(value, str), f"{path}: esperado string"
    elif kind == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), f"{path}: esperado inteiro"
    elif kind == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{path}: esperado número"
        )
    elif kind == "boolean":
        assert isinstance(value, bool), f"{path}: esperado booleano"


def response_schema(spec: dict, path: str, method: str, status: str) -> dict:
    response = spec["paths"][path][method]["responses"][status]
    response = resolve(spec, response)
    return response["content"]["application/json"]["schema"]
