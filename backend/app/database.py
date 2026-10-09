"""Database engine and sessions.

The default URL is a local PostgreSQL database. Tests and offline runs can
set DATABASE_URL to a SQLite URL; memory databases share one connection.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_URL = "postgresql+psycopg://anipulse:anipulse@127.0.0.1:5432/anipulse"

_engine = None
_Session: sessionmaker[Session] | None = None


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_URL)


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = database_url()
        if url.startswith("sqlite"):
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            _engine = create_engine(url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _Session is not None
    return _Session


def get_db():
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
