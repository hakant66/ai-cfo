import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.config import settings


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def db_session_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set for Postgres-backed tests.")
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def mock_shopify_settings(monkeypatch):
    monkeypatch.setattr(settings, "shopify_url", "http://mock-shopify:8080")
    monkeypatch.setattr(settings, "shopify_access_token", "mock_token_123")
    monkeypatch.setattr(settings, "shopify_use_graphql", True)
    yield