from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.domain.aggregation import AggregatedObservation, AggregationLevel

# The brief's required input format has no UTC offset: it is a wall-clock
# value whose timezone is supplied separately (the `timezone` field), not
# embedded in the string. This is stricter than Pydantic's default
# datetime parsing, which would also accept an offset-bearing string and
# silently produce an aware datetime, which app.domain.time.to_utc_instant
# explicitly rejects, since pairing a wall-clock value with a timezone is
# this system's job, not the caller's.
_INPUT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class Measurement(Enum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    SPEED = "speed"


class ObservationQuery(BaseModel):
    """Parsed and cross-field-validated request. Built from raw query params
    in the route, not directly from FastAPI's per-parameter validation,
    because "start before end" is a relationship between two fields that
    Pydantic's field-level validation can't express on its own.
    """

    model_config = ConfigDict(frozen=True)

    station: str
    start: datetime
    end: datetime
    timezone: str | None
    aggregation: AggregationLevel
    measurements: frozenset[Measurement]

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse_naive_local_datetime(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        try:
            return datetime.strptime(value, _INPUT_DATETIME_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"{value!r} does not match required format YYYY-MM-DDTHH:MM:SS"
            ) from exc

    @model_validator(mode="after")
    def _check_start_before_end(self) -> "ObservationQuery":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class ObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    datetime: datetime
    temperature_celsius: float | None = None
    pressure_hpa: float | None = None
    wind_speed_ms: float | None = None
    # Alongside the mean, not a separately selectable measurement: turbine
    # power generation has minimum, maximum, and optimal operating wind
    # speeds, confirmed with the assigning team, so a mean alone can
    # conceal operationally significant behavior a feasibility study needs.
    wind_speed_max_ms: float | None = None
    observation_count: int


class LatestAvailableResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    latest_available_date: date | None


def to_response(
    aggregated: AggregatedObservation, measurements: frozenset[Measurement]
) -> ObservationResponse:
    speed_requested = Measurement.SPEED in measurements
    return ObservationResponse(
        datetime=aggregated.bucket_start,
        temperature_celsius=(
            aggregated.temperature_celsius if Measurement.TEMPERATURE in measurements else None
        ),
        pressure_hpa=aggregated.pressure_hpa if Measurement.PRESSURE in measurements else None,
        wind_speed_ms=aggregated.wind_speed_ms if speed_requested else None,
        wind_speed_max_ms=aggregated.wind_speed_max_ms if speed_requested else None,
        observation_count=aggregated.observation_count,
    )
