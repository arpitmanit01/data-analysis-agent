"""CSV loading and profiling tool.

Loads a CSV into a pandas DataFrame and produces a compact, human-readable
profile (shape, dtypes, null counts, sample rows, numeric summary) that is
injected into agent prompts as grounding context.
"""

from __future__ import annotations

import os

import pandas as pd


class CSVValidationError(ValueError):
    """Raised when the provided CSV path is invalid or unreadable."""


def load_csv(path: str, *, max_mb: float = 100.0) -> pd.DataFrame:
    """Load a CSV with basic input validation and guardrails."""
    if not path:
        raise CSVValidationError("No CSV path provided.")
    if not os.path.exists(path):
        raise CSVValidationError(f"CSV file not found: {path}")
    if not os.path.isfile(path):
        raise CSVValidationError(f"Path is not a file: {path}")

    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > max_mb:
        raise CSVValidationError(
            f"CSV is {size_mb:.1f} MB, exceeding the {max_mb:.0f} MB limit."
        )

    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        raise CSVValidationError(f"Failed to parse CSV: {exc}") from exc

    if df.empty:
        raise CSVValidationError("CSV loaded but contains no rows.")
    return df


def profile_dataframe(df: pd.DataFrame, *, sample_rows: int = 5) -> str:
    """Return a compact, prompt-friendly profile of the DataFrame."""
    lines: list[str] = []
    lines.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    lines.append("")

    lines.append("Columns (name, dtype, non-null, nulls, unique):")
    for col in df.columns:
        s = df[col]
        lines.append(
            f"  - {col}: {s.dtype}, non_null={int(s.notna().sum())}, "
            f"nulls={int(s.isna().sum())}, unique={int(s.nunique(dropna=True))}"
        )
    lines.append("")

    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        lines.append("Numeric summary:")
        try:
            lines.append(numeric.describe().round(3).to_string())
        except Exception:  # pragma: no cover
            lines.append("  (summary unavailable)")
        lines.append("")

    lines.append(f"First {min(sample_rows, len(df))} rows:")
    try:
        lines.append(df.head(sample_rows).to_string(index=False))
    except Exception:  # pragma: no cover
        lines.append("  (sample unavailable)")

    return "\n".join(lines)


def load_and_profile(path: str) -> tuple[pd.DataFrame, str]:
    """Convenience: load a CSV and return the DataFrame plus its profile."""
    df = load_csv(path)
    return df, profile_dataframe(df)
