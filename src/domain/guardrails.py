"""Guardrails determinísticos aplicados antes e depois do LLM."""
import re
import unicodedata

from src.domain.errors import InvalidQuestion

MAX_QUESTION_LEN = 500

_PII_PATTERNS = {
    "CPF": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "telefone": re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"),
}

_INJECTION_PATTERNS = [
    re.compile(r"ignor\w*\s+(as|todas|tudo|all|previous|prior)"),
    re.compile(r"desconsider\w*\s+(as|todas|tudo)"),
    re.compile(r"esquec\w*\s+(as|tudo|todas|suas)\s+(instruc|regras|orienta)"),
    re.compile(r"(system prompt|prompt do sistema|prompt de sistema)"),
    re.compile(r"(you are now|voce agora e|finja ser|aja como|act as)"),
    re.compile(r"(jailbreak|modo desenvolvedor|developer mode)"),
]

_POINT_ID = re.compile(r"\bP-\d{3}\b")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparação."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def sanitize_question(question: str) -> str:
    """Limpa a pergunta e recusa dado pessoal (guardrail G2)."""
    clean = _CONTROL_CHARS.sub(" ", question or "")
    clean = clean.replace("<", " ").replace(">", " ")
    clean = " ".join(clean.split())
    if not clean:
        raise InvalidQuestion("A pergunta está vazia.")
    if len(clean) > MAX_QUESTION_LEN:
        raise InvalidQuestion(f"A pergunta excede {MAX_QUESTION_LEN} caracteres.")
    for label, pattern in _PII_PATTERNS.items():
        if pattern.search(clean):
            raise InvalidQuestion(
                f"A pergunta parece conter dado pessoal ({label}). Remova e tente de novo."
            )
    return clean


def is_injection(clean_question: str) -> bool:
    text = normalize(clean_question)
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def verify_answer(answer_text: str, allowed_ids: set) -> bool:
    """Guardrail G1: a resposta só pode citar pontos presentes nos dados."""
    if not answer_text or not answer_text.strip():
        return False
    cited = set(_POINT_ID.findall(answer_text))
    return cited.issubset(allowed_ids)
