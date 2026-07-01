"""Structured, inspectable per-step logging for the agent's reasoning trace.

Every agent step appends a `TraceEvent` to an in-memory trace *and* emits a
standard log line, so a full reason -> plan -> act -> observe -> respond chain
can be replayed or persisted for the run report.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field

_LOGGER_NAME = "data_analysis_agent"


def get_logger() -> logging.Logger:
    """Return the package logger, configuring a stream handler once."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


@dataclass
class TraceEvent:
    """A single step in the agent's reasoning trace."""

    step: str
    phase: str  # one of: reason, plan, act, observe, respond
    detail: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class Tracer:
    """Collects `TraceEvent`s and mirrors them to the logger."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []
        self._log = get_logger()

    def record(self, step: str, phase: str, detail: str, **data) -> TraceEvent:
        event = TraceEvent(step=step, phase=phase, detail=detail, data=data)
        self.events.append(event)
        self._log.info("[%s/%s] %s", phase, step, detail)
        return event

    def as_list(self) -> list[dict]:
        return [e.to_dict() for e in self.events]

    def dumps(self, indent: int = 2) -> str:
        return json.dumps(self.as_list(), indent=indent, default=str)
