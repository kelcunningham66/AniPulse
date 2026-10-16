"""Database engine and sessions.

The default URL is a local PostgreSQL database. Tests and offline runs can
set DATABASE_URL to a SQLite URL; memory databases share one connection.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_URL = "postgresql+psycopg://anipulse:anipulse@127.0.0.1:5432/anipulse"

_engine = None
_Session: sessionmaker[Session] | None = None


def database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    # Vercel has no local Postgres. The demo catalog is seeded into a file
    # on the instance, and a cold start loads it again.
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/anipulse.db"
    return DEFAULT_URL


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


def ensure_user_columns() -> None:
    """Add alert columns on databases created before notifications shipped."""
    engine = get_engine()
    tables = inspect(engine).get_table_names()
    if "users" not in tables:
        return
    have = {column["name"] for column in inspect(engine).get_columns("users")}
    flag = "TRUE" if engine.dialect.name.startswith("postgres") else "1"
    off = "FALSE" if engine.dialect.name.startswith("postgres") else "0"
    additions = {
        "notify_in_app": f"BOOLEAN DEFAULT {flag}",
        "notify_email": f"BOOLEAN DEFAULT {flag}",
        "notify_push": f"BOOLEAN DEFAULT {off}",
        "notify_episodes": f"BOOLEAN DEFAULT {flag}",
        "notify_dubs": f"BOOLEAN DEFAULT {flag}",
        "notify_delays": f"BOOLEAN DEFAULT {flag}",
        "notify_renewals": f"BOOLEAN DEFAULT {flag}",
        "notify_streaming": f"BOOLEAN DEFAULT {flag}",
        "email_address": "VARCHAR(160) DEFAULT ''",
        "push_token": "VARCHAR(512) DEFAULT ''",
    }
    with engine.begin() as connection:
        for name, ddl in additions.items():
            if name not in have:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


def get_db():
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
