"""AniPulse API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import get_engine, session_factory
from app.models import Base
from app.routers.api import router
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(get_engine())
    db = session_factory()()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="AniPulse AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


def _spa_index() -> Path | None:
    candidates = (
        Path.cwd() / "public" / "index.html",
        Path(__file__).resolve().parents[2] / "public" / "index.html",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


@app.get("/", include_in_schema=False)
def root():
    index = _spa_index()
    if index is not None:
        return FileResponse(index)
    return {"service": "AniPulse AI", "docs": "/docs"}


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """Serve the built dashboard for client-side routes such as /feed."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    if "." in Path(full_path).name:
        raise HTTPException(status_code=404, detail="Not found")
    index = _spa_index()
    if index is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(index)
