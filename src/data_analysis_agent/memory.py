"""Conversation-memory persistence via a SQLite checkpointer.

LangGraph checkpointers persist graph state per `thread_id`, giving us
cross-session memory: resuming the same thread restores prior context (e.g. the
CSV profile and earlier clarifications).
"""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from .config import get_settings


def build_checkpointer() -> SqliteSaver:
    """Create a persistent SQLite checkpointer at the configured path."""
    settings = get_settings()
    conn = sqlite3.connect(settings.memory_db, check_same_thread=False)
    return SqliteSaver(conn)
