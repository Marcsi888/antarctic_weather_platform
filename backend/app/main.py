from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes.observations import router as observations_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_sqlite_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.settings = settings

    # One AsyncClient and one engine for the app's lifetime: both hold
    # pooled connections that should be reused across requests, not
    # rebuilt per request (see app/api/dependencies.py's docstring on
    # connection reuse).
    timeout = httpx.Timeout(settings.aemet_request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as http_client:
        app.state.http_client = http_client
        app.state.db_engine = create_sqlite_engine(settings.database_path)
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Antarctic Weather Platform", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(observations_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
