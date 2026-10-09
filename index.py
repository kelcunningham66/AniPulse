"""Vercel entrypoint.

The API package lives in backend/. This module puts that directory on the
path and re-exports the FastAPI app Vercel looks for.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.main import app

__all__ = ["app"]
