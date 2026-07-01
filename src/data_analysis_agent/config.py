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
        return bool(self.api_key)


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
