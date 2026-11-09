"""Camada HTTP. Traduz requisições para casos de uso e erros de domínio para status."""
import time
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.schemas import (
    AskRequest,
    AskResponse,
    ErrorBody,
    HealthOut,
    MetricsOut,
    PointOut,
    PointPage,
)
from src.domain.errors import DomainError, InvalidQuestion, LlmUnavailable, PointNotFound
from src.domain.models import PointStatus
from src.domain.services import AskService, PointService
from src.infra.config import Settings, build_llm
from src.infra.observability import Metrics, log_event
from src.infra.repository_json import JsonPointRepository

_STATUS_BY_ERROR = (
    (PointNotFound, 404),
    (InvalidQuestion, 422),
    (LlmUnavailable, 503),
)


def _err(description: str) -> dict:
    return {"model": ErrorBody, "description": description}


def _error_response(request: Request, status_code: int, code: str, message: str):
    body = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    return JSONResponse(status_code=status_code, content=body)


def create_app(
    points: PointService,
    asker: AskService,
    metrics: Optional[Metrics] = None,
    llm_provider: str = "fake",
) -> FastAPI:
    metrics = metrics or Metrics()
    app = FastAPI(title="CitizenTech Mobilidade API", version="1.0.0")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            metrics.record_request(status_code, latency_ms)
            log_event(
                "request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=status_code,
                latency_ms=round(latency_ms, 2),
            )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        for error_type, status_code in _STATUS_BY_ERROR:
            if isinstance(exc, error_type):
                return _error_response(request, status_code, exc.code, exc.message)
        return _error_response(request, 500, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        broken_json = any(e.get("type") == "json_invalid" for e in errors)
        in_body = any(e["loc"] and e["loc"][0] == "body" for e in errors)
        status_code = 422 if (in_body and not broken_json) else 400
        message = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in errors
        )
        return _error_response(request, status_code, "VALIDATION_ERROR", message)

    @app.get("/health", response_model=HealthOut, tags=["operacao"])
    def health():
        return HealthOut(status="ok", llm_provider=llm_provider)

    @app.get("/metrics", response_model=MetricsOut, tags=["operacao"])
    def get_metrics():
        return MetricsOut(**metrics.snapshot())

    @app.get(
        "/points",
        response_model=PointPage,
        responses={400: _err("Parâmetro de consulta inválido")},
        tags=["pontos"],
    )
    def list_points(
        status: Optional[PointStatus] = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        page = points.list_points(status, limit, offset)
        next_offset = offset + limit if offset + limit < page.total else None
        return PointPage(
            items=[PointOut(**asdict(p)) for p in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            next_offset=next_offset,
        )

    @app.get(
        "/points/{point_id}",
        response_model=PointOut,
        responses={404: _err("Ponto não encontrado")},
        tags=["pontos"],
    )
    def get_point(point_id: str):
        return PointOut(**asdict(points.get_point(point_id)))

    @app.post(
        "/ask",
        response_model=AskResponse,
        responses={
            400: _err("JSON malformado"),
            404: _err("point_id informado não existe"),
            422: _err("Pergunta inválida ou com dado pessoal"),
            503: _err("Modelo de linguagem indisponível"),
        },
        tags=["ia"],
    )
    def ask(body: AskRequest):
        try:
            answer = asker.ask(body.question, body.point_id)
        except LlmUnavailable:
            metrics.record_llm_failure()
            log_event("ask_failed", reason="LLM_UNAVAILABLE")
            raise
        metrics.record_ask(answer)
        log_event(
            "ask",
            refused=answer.refused,
            refusal_reason=answer.refusal_reason.value if answer.refusal_reason else None,
            model=answer.model,
            tokens_in=answer.tokens_in,
            tokens_out=answer.tokens_out,
        )
        return AskResponse(
            answer=answer.text,
            refused=answer.refused,
            refusal_reason=answer.refusal_reason,
            sources=answer.sources,
            model=answer.model,
        )

    return app


def build_default_app() -> FastAPI:
    settings = Settings.from_env()
    repository = JsonPointRepository(settings.data_path)
    return create_app(
        PointService(repository),
        AskService(repository, build_llm(settings)),
        Metrics(),
        settings.llm_provider,
    )


app = build_default_app()
