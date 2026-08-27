from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import PersistenceError
from app.db.models import FetchedRange, ObservationRecord
from app.db.session import session_scope
from app.integrations.aemet.schemas import Station, StationObservation


class ObservationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def is_range_cached(self, station: Station, start: datetime, end: datetime) -> bool:
        """True if a single prior fetch already covers [start, end]."""
        # Containment against one stored range, not a union of many a
        # deliberate scope limit (see README: Database and Cache Strategy).
        try:
            with session_scope(self._session_factory) as session:
                covering_range = session.execute(
                    select(FetchedRange.id).where(
                        FetchedRange.station == station,
                        FetchedRange.range_start <= start,
                        FetchedRange.range_end >= end,
                    )
                ).first()
                return covering_range is not None
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to check cache coverage") from exc

    def get_latest_observed_at(self, station: Station) -> datetime | None:
        """Most recent cached observation for a station, or None if nothing is cached yet."""
        try:
            with session_scope(self._session_factory) as session:
                return session.execute(
                    select(func.max(ObservationRecord.observed_at)).where(
                        ObservationRecord.station == station
                    )
                ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to read latest cached observation") from exc

    def get_observations(
        self, station: Station, start: datetime, end: datetime
    ) -> list[StationObservation]:
        try:
            with session_scope(self._session_factory) as session:
                rows = (
                    session.execute(
                        select(ObservationRecord)
                        .where(
                            ObservationRecord.station == station,
                            ObservationRecord.observed_at >= start,
                            ObservationRecord.observed_at <= end,
                        )
                        .order_by(ObservationRecord.observed_at)
                    )
                    .scalars()
                    .all()
                )
                return [_to_domain(row) for row in rows]
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to read cached observations") from exc

    def store_fetch_result(
        self,
        station: Station,
        start: datetime,
        end: datetime,
        observations: list[StationObservation],
    ) -> None:
        """Persist observations and mark the range fetched, as one transaction."""
        # Both writes succeed or fail together, or the two tables could
        # disagree about what "cached" means.
        try:
            with session_scope(self._session_factory) as session:
                if observations:
                    # merge() upserts on the ORM primary key (id), which
                    # every fresh StationObservation lacks, so it would
                    # always insert and violate the (station, observed_at)
                    # unique constraint on any overlap between fetches.
                    # An explicit ON CONFLICT upsert targets that business
                    # key directly.
                    values = [_to_row_values(station, obs) for obs in observations]
                    stmt = sqlite_insert(ObservationRecord).values(values)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["station", "observed_at"],
                        set_={
                            "temperature_celsius": stmt.excluded.temperature_celsius,
                            "pressure_hpa": stmt.excluded.pressure_hpa,
                            "wind_speed_ms": stmt.excluded.wind_speed_ms,
                            "is_good_quality": stmt.excluded.is_good_quality,
                        },
                    )
                    session.execute(stmt)
                session.add(FetchedRange(station=station, range_start=start, range_end=end))
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to store fetch result") from exc


def _to_domain(row: ObservationRecord) -> StationObservation:
    # Deliberately returns the raw stored values, not nulled by quality:
    # the qdato=1 -> null policy is applied in exactly one place
    # (app.domain.aggregation), whether observations came from cache or a
    # fresh AEMET call, so the policy can change without needing a re-fetch.
    return StationObservation(
        station=row.station,
        observed_at=row.observed_at,
        temperature_celsius=row.temperature_celsius,
        pressure_hpa=row.pressure_hpa,
        wind_speed_ms=row.wind_speed_ms,
        is_good_quality=row.is_good_quality,
    )


def _to_row_values(station: Station, obs: StationObservation) -> dict[str, object]:
    return {
        "station": station,
        "observed_at": obs.observed_at,
        "temperature_celsius": obs.temperature_celsius,
        "pressure_hpa": obs.pressure_hpa,
        "wind_speed_ms": obs.wind_speed_ms,
        "is_good_quality": obs.is_good_quality,
    }
