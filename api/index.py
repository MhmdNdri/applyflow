"""Vercel ASGI entrypoint for the Applyflow API.

This file lets a second Vercel project deploy the FastAPI backend from the
repo root while the frontend project continues to use `frontend/` as its root.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

os.chdir(ROOT)
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from jobfit_api.main import app  # noqa: E402
