import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies import get_model_version_service
from app.api.routers import (
    apk,
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
from app.application.auth_service import AuthService
from app.config.settings import ConfigurationError, Settings
from app.infrastructure.events.audit_listeners import subscribe_audit_listeners
from app.infrastructure.log.middleware import RequestLogMiddleware, TraceIDMiddleware
from app.infrastructure.log.setup import get_audit_logger, setup_logging
from app.infrastructure.persistence.database import create_session_factory, create_sqlite_engine
from app.infrastructure.persistence.migrations import upgrade_database
from app.infrastructure.persistence.repositories.user_sqlalchemy_repository import (
    SqlAlchemyUserRepository,
)
from app.infrastructure.security.middleware import SecurityHeadersMiddleware

logger = logging.getLogger("app")


def _configure_app(app: FastAPI, settings: Settings, session_factory: object) -> None:
    app.state.settings = settings
    app.state.session_factory = session_factory

    session = session_factory()  # type: ignore[operator]
    try:
        auth_service = AuthService(SqlAlchemyUserRepository(session), settings)
        auth_service.ensure_initial_administrator()
        mvs = get_model_version_service(session)
        app.state.model_version_service = mvs
        session.commit()
    finally:
        session.close()
    logger.info("App configured for environment: %s", settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        settings = Settings.from_env()
    except ConfigurationError as e:
        logger.critical("Configuration error: %s", e)
        raise

    app.state.settings = settings
    setup_logging(settings.environment.upper() if settings.environment != "testing" else "DEBUG")
    audit_log = get_audit_logger("app")
    audit_log.info("Application starting in %s mode", settings.environment)

    if settings.database_url.startswith("sqlite"):
        upgrade_database(settings.database_url)

    engine = create_sqlite_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    _configure_app(app, settings, session_factory)
    subscribe_audit_listeners()

    yield

    engine.dispose()
    audit_log.info("Application shutting down")


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException:
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    application = FastAPI(title="Indoor Positioning Platform", version="0.1.0", lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(TraceIDMiddleware)
    application.add_middleware(RequestLogMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)

    application.include_router(apk.router)
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

    admin_dist = Path("/app/admin-portal-dist")
    if admin_dist.is_dir():
        from os import getenv

        if getenv("SERVE_ADMIN_PORTAL", "false").lower() in ("true", "1", "yes"):
            application.mount(
                "/", SPAStaticFiles(directory=str(admin_dist), html=True), name="admin-portal"
            )

    return application


app = create_app()
