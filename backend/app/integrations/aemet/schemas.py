from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class Station(Enum):
    GABRIEL_DE_CASTILLA = "89070"
    JUAN_CARLOS_I = "89064"


class AemetEnvelope(BaseModel):
    """The first-step response from the antartida/datos endpoint.

    AEMET's API is a two-step indirection: this call never returns
    observations directly, only URLs to fetch them from (see `datos`)
    and to fetch their field descriptions from (see `metadatos`).
    """

    model_config = ConfigDict(extra="ignore")

    estado: int
    descripcion: str
    datos: str
    metadatos: str


class AemetObservationDTO(BaseModel):
    """One record from the `datos` URL, as AEMET actually sends it.

    AEMET's payload carries ~25 fields (humidity, wind direction, solar
    radiation, soil temperature...) and the field set differs by station
    type; only the fields this application needs are declared here, and
    everything else is dropped by `extra="ignore"` rather than rejected.
    Fields AEMET doesn't measure for a given station/interval appear as
    the literal string "NaN", not JSON null or a missing key.
    """

    model_config = ConfigDict(extra="ignore")

    identificacion: str
    fhora: datetime
    temp: float | None = None
    pres: float | None = None
    vel: float | None = None
    qdato: float | None = None

    @field_validator("temp", "pres", "vel", "qdato", mode="before")
    @classmethod
    def _nan_sentinel_to_none(cls, value: object) -> object:
        # A bare float("nan") would satisfy the `float | None` type but
        # poison any downstream sum/mean silently (nan propagates through
        # arithmetic without raising). Treating AEMET's sentinel as an
        # explicit None keeps "not measured" a checkable, filterable state.
        if isinstance(value, str) and value.strip().lower() == "nan":
            return None
        return value


class StationObservation(BaseModel):
    """A single verified, in-domain reading. What the rest of the app sees."""

    model_config = ConfigDict(frozen=True)

    station: Station
    observed_at: datetime
    temperature_celsius: float | None
    pressure_hpa: float | None
    wind_speed_ms: float | None
    is_good_quality: bool


def map_to_observation(dto: AemetObservationDTO) -> StationObservation:
    return StationObservation(
        station=Station(dto.identificacion),
        observed_at=dto.fhora,
        temperature_celsius=dto.temp,
        pressure_hpa=dto.pres,
        wind_speed_ms=dto.vel,
        # qdato is undocumented as ever being absent in practice, but the
        # DTO models it as optional; treat a missing flag as good quality
        # rather than silently discarding the observation from aggregation.
        is_good_quality=dto.qdato != 1.0,
    )
