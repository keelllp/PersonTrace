import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_app
from app.models import Base

from .fakes import FakeStorage


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def fake_storage():
    return FakeStorage()


@pytest.fixture()
def processor_calls():
    return []


@pytest.fixture()
def app(session_factory, fake_storage, processor_calls):
    def processor(job_id, cancel_check):
        processor_calls.append(job_id)

    application = create_app(storage=fake_storage, processor=processor)
    application.state.job_queue._session_factory = session_factory

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = override_get_db
    application.state.job_queue.submit = application.state.job_queue._run
    return application


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def auth_client(client):
    def _make(email="user@test.com", password="secret123"):
        r = client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        assert r.status_code == 201, r.text
        return client

    return _make
