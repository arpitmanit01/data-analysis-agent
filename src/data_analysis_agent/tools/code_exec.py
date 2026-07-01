"""Lightweight sandboxed execution of LLM-generated analysis code.

Design choice (confirmed with the user): a *simple* in-process `exec` with
minimal guarding, favouring speed of development over strong isolation. We
still add pragmatic guardrails:

  * an AST scan that blocks a denylist of dangerous imports / calls,
  * a hard denylist of dunder / os-level escape patterns,
  * a wall-clock timeout enforced via a worker thread,
  * stdout capture and matplotlib artifact collection.

TRADEOFF: a worker thread cannot be force-killed in CPython, and in-process
`exec` shares the interpreter, so this is NOT a security boundary against
adversarial code. It is documented in `wikis/`. For untrusted input, swap this
module for subprocess/Docker isolation.
"""

from __future__ import annotations

import ast
import io
import os
import queue
import threading
from contextlib import redirect_stdout
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")  # headless backend for server/CLI use
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import get_settings  # noqa: E402
from ..logging_utils import get_logger  # noqa: E402

_log = get_logger()

# Modules that must never be imported by generated code.
_BLOCKED_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "http",
    "pickle",
    "importlib",
    "ctypes",
    "pathlib",
    "glob",
    "builtins",
}

# Dangerous attribute/name patterns.
_BLOCKED_TOKENS = {
    "__import__",
    "__builtins__",
    "__subclasses__",
    "__globals__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
}


@dataclass
class ExecutionResult:
    """Outcome of executing a generated code block."""

    ok: bool
    stdout: str
    result_value: str
    error: str
    artifacts: list[str]

    def as_observation(self) -> str:
        """Format the result for the agent to observe."""
        if not self.ok:
            return f"EXECUTION FAILED:\n{self.error}"
        parts = []
        if self.stdout.strip():
            parts.append("STDOUT:\n" + self.stdout.strip())
        if self.result_value:
            parts.append("RESULT:\n" + self.result_value)
        if self.artifacts:
            parts.append("ARTIFACTS: " + ", ".join(self.artifacts))
        return "\n\n".join(parts) or "(no output produced)"


def static_guard(code: str) -> str | None:
    """Return an error message if the code violates guardrails, else None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError before execution: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_IMPORTS:
                    return f"Blocked import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BLOCKED_IMPORTS:
                return f"Blocked import from: {node.module}"
        elif isinstance(node, ast.Attribute):
            if node.attr in _BLOCKED_TOKENS:
                return f"Blocked attribute access: {node.attr}"
        elif isinstance(node, ast.Name):
            if node.id in _BLOCKED_TOKENS:
                return f"Blocked name: {node.id}"
    return None


def _new_artifacts(before: set[str], artifacts_dir: str) -> list[str]:
    after = set(os.listdir(artifacts_dir)) if os.path.isdir(artifacts_dir) else set()
    return sorted(after - before)


def execute_code(code: str, df: pd.DataFrame, *, timeout: int | None = None) -> ExecutionResult:
    """Execute `code` with `df` in scope, capturing output and artifacts."""
    settings = get_settings()
    timeout = timeout or settings.code_timeout

    guard_error = static_guard(code)
    if guard_error:
        _log.warning("Guardrail blocked code: %s", guard_error)
        return ExecutionResult(False, "", "", guard_error, [])

    artifacts_dir = settings.artifacts_dir
    os.makedirs(artifacts_dir, exist_ok=True)
    before = set(os.listdir(artifacts_dir))

    # Namespace given to the generated code.
    sandbox_globals: dict = {
        "pd": pd,
        "np": np,
        "plt": plt,
        "df": df,
        "ARTIFACTS_DIR": artifacts_dir,
    }

    result_q: queue.Queue = queue.Queue()

    def _run() -> None:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(code, sandbox_globals)  # noqa: S102 - sandboxed by design
            result_val = sandbox_globals.get("result", "")
            result_q.put(("ok", buf.getvalue(), str(result_val), ""))
        except Exception as exc:  # noqa: BLE001
            import traceback

            result_q.put(("err", buf.getvalue(), "", traceback.format_exc(limit=3)))

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout)

    if worker.is_alive():
        _log.error("Code execution exceeded %ss timeout.", timeout)
        return ExecutionResult(
            False, "", "", f"Execution timed out after {timeout}s.", []
        )

    try:
        status, stdout, result_val, error = result_q.get_nowait()
    except queue.Empty:  # pragma: no cover
        return ExecutionResult(False, "", "", "No result produced.", [])
    finally:
        plt.close("all")

    artifacts = _new_artifacts(before, artifacts_dir)
    if status == "ok":
        return ExecutionResult(True, stdout, result_val, "", artifacts)
    return ExecutionResult(False, stdout, "", error, artifacts)
