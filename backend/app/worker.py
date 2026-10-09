"""Celery entrypoint for the source scan.

The API runs the same job inline when Redis is not configured, so the demo
does not depend on a broker. Set CELERY_BROKER_URL and run this worker when
you want the queue.
"""

from __future__ import annotations

import os

from celery import Celery

broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery = Celery("anipulse", broker=broker, backend=os.getenv("CELERY_RESULT_BACKEND", broker))


@celery.task(name="anipulse.scan")
def scan_task() -> dict:
    from app.database import session_factory
    from app.services.pipeline import process_pending

    db = session_factory()()
    try:
        return process_pending(db)
    finally:
        db.close()
