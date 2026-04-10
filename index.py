"""Vercel FastAPI entrypoint for Applyflow."""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

os.chdir(ROOT)
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jobfit_api.main import app  # noqa: E402
