from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.db.repository import ObservationRepository
from app.db.session import make_session_factory
from app.integrations.aemet.client import AemetClient
from app.services.weather_service import WeatherService


def get_weather_service(request: Request) -> WeatherService:
    # Reuses the lifespan-scoped httpx client and SQLite engine from
    # app.state; only the cheap per-request objects are built fresh here.
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
