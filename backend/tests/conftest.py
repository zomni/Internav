import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.dependencies import get_model_version_service
from app.api.routers import (
    auth,
    campaigns,
    datasets,
    fingerprints,
    floor_plans,
    grids,
    hierarchy,
    inference,
    models,
    users,
)
from app.config.settings import Settings
from app.domain.entities.user import User, UserRole
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.repositories.user_sqlalchemy_repository import (
    SqlAlchemyUserRepository,
)
from app.security.passwords import hash_password


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def settings():
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret_key="test-secret-key-for-testing-only",
        jwt_access_token_minutes=30,
        jwt_refresh_token_days=7,
        admin_email="admin@test.com",
        admin_password="Admin123!",
        model_storage_path="./test_models",
    )


def _create_test_app(sf, st) -> FastAPI:
    application = FastAPI()
    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(hierarchy.router, prefix="/api/v1")
    application.include_router(floor_plans.router, prefix="/api/v1")
    application.include_router(grids.router, prefix="/api/v1")
    application.include_router(campaigns.router, prefix="/api/v1")
    application.include_router(datasets.router, prefix="/api/v1")
    application.include_router(fingerprints.router, prefix="/api/v1")
    application.include_router(models.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(inference.router, prefix="/api/v1")
    application.state.session_factory = sf
    application.state.settings = st
    _configure_test_app(application)
    return application


def _configure_test_app(application: FastAPI) -> None:
    session = application.state.session_factory()
    try:
        mvs = get_model_version_service(session)
        application.state.model_version_service = mvs
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def client(session_factory, settings):
    test_app = _create_test_app(session_factory, settings)
    with TestClient(test_app) as c:
        yield c


@pytest.fixture()
def seed_admin(session_factory):
    session = session_factory()
    try:
        repo = SqlAlchemyUserRepository(session)
        repo.add(
            User(
                email="admin@test.com",
                password_hash=hash_password("Admin123!"),
                role=UserRole.ADMINISTRATOR,
            )
        )
        session.commit()
    finally:
        session.close()


def login_admin(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"},
    )
    return resp.json()["data"]["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
