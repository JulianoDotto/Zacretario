import os

import pytest
from sqlalchemy.orm import Session

import zacretario.models  # noqa: F401  (registers the tables on Base.metadata)
from zacretario.db import Base, make_session_factory

# Postgres from docker-compose when TEST_DATABASE_URL is set; in-memory SQLite otherwise.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture
def session():
    factory = make_session_factory(TEST_DATABASE_URL)
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine)
    db_session: Session = factory()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
