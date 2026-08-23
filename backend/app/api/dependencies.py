from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.db.repository import ObservationRepository
from app.db.session import make_session_factory
from app.integrations.aemet.client import AemetClient
from app.services.weather_service import WeatherService


def get_weather_service(request: Request) -> WeatherService:
    """Constructs a WeatherService from objects the lifespan attached to
    app.state (the shared httpx.AsyncClient) plus fresh, cheap objects
    (session factory, repository) built per request. The SQLite engine
    itself is also lifespan-scoped: it owns no long-lived connection by
    default, but re-running schema creation and file-existence checks on
    every request would be wasted work for no benefit.
    """
    settings: Settings = request.app.state.settings
    http_client: httpx.AsyncClient = request.app.state.http_client

    aemet_client = AemetClient(
        http_client=http_client,
        api_key=settings.aemet_api_key,
        base_url=str(settings.aemet_base_url),
    )
    session_factory = make_session_factory(request.app.state.db_engine)
    repository = ObservationRepository(session_factory)
    return WeatherService(aemet_client, repository)


WeatherServiceDep = Annotated[WeatherService, Depends(get_weather_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
