"""Centralized, externalized configuration.

All tunables (model, temperature, keys, timeouts, guardrail limits) are read
from environment variables / the `.env` file so nothing is hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv

# Load .env once at import time (override any stale process env values).
load_dotenv(find_dotenv(), override=True)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    api_key: str | None
    base_url: str
    model: str
    temperature: float
    timeout: int
    max_retries: int
    max_input_tokens: int
    code_timeout: int
    memory_db: str
    artifacts_dir: str

    @property
    def has_api_key(self) -> bool:
        key = (self.api_key or "").strip()
        return bool(key) and key.lower() not in _PLACEHOLDER_VALUES


# Values shipped in `.env.example`; treated as "not configured" so a user who
# copies the template without editing it gets a clear message instead of a 401.
_PLACEHOLDER_VALUES = {
    "your-azure-ai-foundry-key-here",
    "your-key-here",
    "your-api-key-here",
    "changeme",
    "todo",
}


def validate_settings(settings: "Settings | None" = None) -> list[str]:
    """Return a list of human-readable configuration problems (empty if OK)."""
    settings = settings or get_settings()
    problems: list[str] = []

    key = (settings.api_key or "").strip()
    if not key:
        problems.append(
            "AZURE_AI_API_KEY is not set (also accepts AZURE_OPENAI_API_KEY)."
        )
    elif key.lower() in _PLACEHOLDER_VALUES:
        problems.append(
            "AZURE_AI_API_KEY still holds the .env.example placeholder value; "
            "replace it with your real key."
        )

    if not settings.base_url.strip():
        problems.append("DAA_LLM_BASE_URL is empty.")
    if not settings.model.strip():
        problems.append("DAA_LLM_MODEL is empty.")

    return problems


def config_error_message(settings: "Settings | None" = None) -> str | None:
    """Return a single actionable error string if config is invalid, else None.

    Shared by every entrypoint (CLI, evaluation, Streamlit UI, LLM factory) so
    the app fails gracefully with one consistent message no matter how it runs.
    """
    problems = validate_settings(settings)
    if not problems:
        return None
    bullets = "\n".join(f"  - {p}" for p in problems)
    return (
        "Configuration problem detected:\n"
        f"{bullets}\n\n"
        "Fix: copy .env.example to .env and set your credentials "
        "(cp .env.example .env). See .env.example for all available options."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings snapshot."""
    return Settings(
        # The reference notebook authenticates with AZURE_AI_API_KEY.
        api_key=os.getenv("AZURE_AI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=os.getenv(
            "DAA_LLM_BASE_URL",
            "https://vermaarpit-aifoundry1-s.cognitiveservices.azure.com/models",
        ),
        model=os.getenv("DAA_LLM_MODEL", "gpt-5.4"),
        temperature=_get_float("DAA_LLM_TEMPERATURE", 0.1),
        timeout=_get_int("DAA_LLM_TIMEOUT", 60),
        max_retries=_get_int("DAA_LLM_MAX_RETRIES", 3),
        max_input_tokens=_get_int("DAA_MAX_INPUT_TOKENS", 100_000),
        code_timeout=_get_int("DAA_CODE_TIMEOUT", 30),
        memory_db=os.getenv("DAA_MEMORY_DB", ".agent_memory.sqlite3"),
        artifacts_dir=os.getenv("DAA_ARTIFACTS_DIR", "artifacts"),
    )
