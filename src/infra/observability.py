"""Métricas em memória e log estruturado em JSON."""
import json
import logging
import math
import threading
from collections import deque

logger = logging.getLogger("citizentech")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def log_event(event: str, **fields) -> None:
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False))


class Metrics:
    def __init__(self, window: int = 1000):
        self._lock = threading.Lock()
        self._latencies = deque(maxlen=window)
        self._requests = 0
        self._errors_5xx = 0
        self._asks = 0
        self._refusals = 0
        self._llm_failures = 0
        self._tokens_in = 0
        self._tokens_out = 0

    def record_request(self, status: int, latency_ms: float) -> None:
        with self._lock:
            self._requests += 1
            self._latencies.append(latency_ms)
            if status >= 500:
                self._errors_5xx += 1

    def record_ask(self, answer) -> None:
        with self._lock:
            self._asks += 1
            self._refusals += 1 if answer.refused else 0
            self._tokens_in += answer.tokens_in
            self._tokens_out += answer.tokens_out

    def record_llm_failure(self) -> None:
        with self._lock:
            self._llm_failures += 1

    @staticmethod
    def _ratio(part: int, total: int) -> float:
        return round(part / total, 4) if total else 0.0

    def snapshot(self) -> dict:
        with self._lock:
            lat = sorted(self._latencies)
            p95 = lat[max(math.ceil(0.95 * len(lat)) - 1, 0)] if lat else 0.0
            return {
                "requests_total": self._requests,
                "errors_5xx_total": self._errors_5xx,
                "error_rate": self._ratio(self._errors_5xx, self._requests),
                "latency_p95_ms": round(p95, 2),
                "asks_total": self._asks,
                "refusals_total": self._refusals,
                "refusal_rate": self._ratio(self._refusals, self._asks),
                "llm_failures_total": self._llm_failures,
                "tokens_in_total": self._tokens_in,
                "tokens_out_total": self._tokens_out,
            }
