"""AniPulse API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Vercel copies this directory to the CDN. check_dir is false so a local API
# process can start before the dashboard has been built.
_frontend = getattr(app, "frontend", None)
if _frontend is not None:
    _frontend("/", directory="public", fallback="index.html", check_dir=False)
