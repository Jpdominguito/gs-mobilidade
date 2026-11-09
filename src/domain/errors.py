"""Erros de domínio. A camada de API os traduz para status HTTP."""


class DomainError(Exception):
    code = "DOMAIN_ERROR"

    def __init__(self, message: str = ""):
        super().__init__(message or self.code)
        self.message = message or self.code


class PointNotFound(DomainError):
    code = "POINT_NOT_FOUND"


class InvalidQuestion(DomainError):
    code = "INVALID_QUESTION"


class LlmUnavailable(DomainError):
    code = "LLM_UNAVAILABLE"
