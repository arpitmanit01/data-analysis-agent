"""LLM factory + resilient invocation.

Builds a LangChain `ChatOpenAI` client pointed at the Azure AI Foundry
OpenAI-compatible endpoint, mirroring the known-good reference notebook:

    ChatOpenAI(api_key=AZURE_AI_API_KEY,
               base_url=".../models",
               model="gpt-5.4")

Adds retries (tenacity), timeouts, structured-output binding, and a
token-limit guardrail with graceful fallback.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import Settings, get_settings
from .logging_utils import get_logger

_log = get_logger()

T = TypeVar("T", bound=BaseModel)


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM cannot be constructed (e.g. missing API key)."""


@lru_cache(maxsize=1)
def get_llm(settings: Settings | None = None) -> ChatOpenAI:
    """Construct the chat model. Cached so the client is reused."""
    settings = settings or get_settings()
    if not settings.has_api_key:
        raise LLMConfigurationError(
            "No API key found. Set AZURE_AI_API_KEY in your .env "
            "(copy .env.example to .env)."
        )
    return ChatOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        temperature=settings.temperature,
        timeout=settings.timeout,
        # We manage retries ourselves via tenacity for consistent logging.
        max_retries=0,
    )


def count_tokens(text: str, model: str | None = None) -> int:
    """Best-effort token count using tiktoken; falls back to a word heuristic."""
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model or get_settings().model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:  # pragma: no cover - heuristic fallback
        return max(1, int(len(text.split()) * 1.3))


def enforce_token_budget(text: str, max_tokens: int | None = None) -> str:
    """Guardrail: truncate `text` if it exceeds the input-token budget."""
    settings = get_settings()
    budget = max_tokens or settings.max_input_tokens
    if count_tokens(text) <= budget:
        return text
    # Truncate conservatively by characters (~4 chars/token) and flag it.
    approx_chars = budget * 4
    _log.warning("Input exceeded token budget (%s); truncating.", budget)
    return text[:approx_chars] + "\n... [truncated to respect token budget] ..."


_TRANSIENT = (Exception,)


def _make_retryer():
    settings = get_settings()
    return retry(
        reraise=True,
        stop=stop_after_attempt(max(1, settings.max_retries)),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        retry=retry_if_exception_type(_TRANSIENT),
    )


def invoke_text(messages: list[BaseMessage], *, fallback: str | None = None) -> str:
    """Invoke the LLM for a free-text response with retries and fallback."""

    @_make_retryer()
    def _call() -> str:
        resp = get_llm().invoke(messages)
        return resp.content if isinstance(resp.content, str) else str(resp.content)

    try:
        return _call()
    except Exception as exc:  # noqa: BLE001 - top-level graceful degradation
        _log.error("LLM text call failed after retries: %s", exc)
        if fallback is not None:
            return fallback
        raise


def invoke_structured(messages: list[BaseMessage], schema: type[T]) -> T:
    """Invoke the LLM and parse into a Pydantic `schema` (structured output)."""

    model = get_llm().with_structured_output(schema)

    @_make_retryer()
    def _call() -> T:
        return model.invoke(messages)  # type: ignore[return-value]

    return _call()
