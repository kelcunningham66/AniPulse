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


@app.get("/")
def root() -> dict:
    return {"service": "AniPulse AI", "docs": "/docs"}
