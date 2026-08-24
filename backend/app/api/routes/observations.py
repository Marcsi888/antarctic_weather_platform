import logging

from fastapi import APIRouter, Query
from pydantic import ValidationError as PydanticValidationError

from app.api.dependencies import WeatherServiceDep
from app.api.schemas import Measurement, ObservationQuery, ObservationResponse, to_response
from app.core.exceptions import UnknownStationError
from app.core.exceptions import ValidationError as AppValidationError
from app.domain.aggregation import AggregationLevel
from app.domain.time import resolve_timezone, to_utc_instant
from app.integrations.aemet.schemas import Station

logger = logging.getLogger(__name__)

router = APIRouter()

_STATION_BY_QUERY_VALUE = {
    "gabriel_de_castilla": Station.GABRIEL_DE_CASTILLA,
    "juan_carlos_i": Station.JUAN_CARLOS_I,
}

_ALL_MEASUREMENTS = frozenset(Measurement)


def _resolve_station(value: str) -> Station:
    try:
        return _STATION_BY_QUERY_VALUE[value]
    except KeyError:
        raise UnknownStationError(value) from None


@router.get("/observations", response_model=list[ObservationResponse])
async def get_observations(
    service: WeatherServiceDep,
    station: str = Query(..., description="gabriel_de_castilla or juan_carlos_i"),
    start: str = Query(..., description="YYYY-MM-DDTHH:MM:SS, local to `timezone`"),
    end: str = Query(..., description="YYYY-MM-DDTHH:MM:SS, local to `timezone`"),
    timezone: str | None = Query(
        None,
        description=(
            "IANA timezone name (e.g. Europe/Berlin) or a fixed UTC offset "
            "(e.g. +02:00, -05:30); defaults to Europe/Madrid if omitted"
        ),
    ),
    aggregation: AggregationLevel = Query(AggregationLevel.NONE),
    measurement: list[Measurement] | None = Query(
        None, description="Repeat to select multiple; omit entirely to receive all three"
    ),
) -> list[ObservationResponse]:
    # start/end are declared `datetime` on ObservationQuery (that's the
    # validated, in-domain type), but a `mode="before"` validator accepts
    # the raw query string and parses it strictly. mypy sees the field's
    # declared type, not the validator's input type, and flags this as a
    # str/datetime mismatch — a real, narrow gap in what mypy can infer
    # about Pydantic's dynamic validation, same as get_settings() in
    # app/core/config.py.
    try:
        query = ObservationQuery(
            station=station,
            start=start,  # type: ignore[arg-type]
            end=end,  # type: ignore[arg-type]
            timezone=timezone,
            aggregation=aggregation,
            measurements=frozenset(measurement) if measurement else _ALL_MEASUREMENTS,
        )
    except PydanticValidationError as exc:
        # Cross-field/format checks (start < end, exact datetime format)
        # live in ObservationQuery's own validators and raise Pydantic's
        # ValidationError; re-raised as our own so the registered
        # ApplicationError handler maps it to 400 like every other
        # domain validation failure, rather than an unhandled 500.
        raise AppValidationError(str(exc)) from exc

    resolved_station = _resolve_station(query.station)
    tz = resolve_timezone(query.timezone) if query.timezone else resolve_timezone("Europe/Madrid")

    start_instant = to_utc_instant(query.start, tz)
    end_instant = to_utc_instant(query.end, tz)

    results = await service.get_observations(
        resolved_station, start_instant, end_instant, query.aggregation
    )

    return [to_response(r, query.measurements) for r in results]
