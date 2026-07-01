"""Convenience entrypoint. Prefer `python src/agent.py ...` (assignment spec).

Running this module forwards to the package CLI so `python main.py --csv ...`
also works from the project root.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from data_analysis_agent.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

