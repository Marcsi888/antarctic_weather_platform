from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.integrations.aemet.schemas import Station


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Round-trips as UTC-aware; SQLite's DATETIME column has no timezone concept."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        assert isinstance(value, datetime)
        return value.replace(tzinfo=UTC)


class ObservationRecord(Base):
    """Identity is (station, observed_at); `id` exists only for ORM convenience."""

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("station", "observed_at", name="uq_observation_identity"),
        Index("ix_observation_station_time", "station", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    station: Mapped[Station] = mapped_column(
        SAEnum(Station, native_enum=False, create_constraint=True)
    )
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    temperature_celsius: Mapped[float | None]
    pressure_hpa: Mapped[float | None]
    wind_speed_ms: Mapped[float | None]
    is_good_quality: Mapped[bool]


class FetchedRange(Base):
    """Tracks that AEMET was queried for (station, range), regardless of results."""

    __tablename__ = "fetched_ranges"

    id: Mapped[int] = mapped_column(primary_key=True)
    station: Mapped[Station] = mapped_column(
        SAEnum(Station, native_enum=False, create_constraint=True)
    )
    range_start: Mapped[datetime] = mapped_column(UTCDateTime)
    range_end: Mapped[datetime] = mapped_column(UTCDateTime)
