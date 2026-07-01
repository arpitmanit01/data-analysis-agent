"""Assignment-spec entrypoint: `python src/agent.py --csv ... --query ...`.

Thin shim that makes the `data_analysis_agent` package importable when this
file is run directly, then delegates to the package CLI.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_analysis_agent.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
