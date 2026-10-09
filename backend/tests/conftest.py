import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest


@pytest.fixture(autouse=True)
def fresh_database():
    from app.database import get_engine, session_factory
    from app.models import Base
    from app.seed import seed_if_empty

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = session_factory()()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield
