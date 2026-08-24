from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import FetchedRange, ObservationRecord
from app.db.session import create_sqlite_engine, make_session_factory, session_scope
from app.integrations.aemet.schemas import Station

UTC = ZoneInfo("UTC")


@pytest.fixture
def session_factory(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "test.db")
    return make_session_factory(engine)


def test_create_sqlite_engine_creates_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "weather.db"

    create_sqlite_engine(db_path)

    assert db_path.parent.is_dir()


def test_insert_and_read_observation(session_factory) -> None:
    with session_scope(session_factory) as session:
        session.add(
            ObservationRecord(
                station=Station.GABRIEL_DE_CASTILLA,
                observed_at=datetime(2024, 1, 15, 0, 0, tzinfo=UTC),
                temperature_celsius=1.4,
                pressure_hpa=984.4,
                wind_speed_ms=7.1,
                is_good_quality=True,
            )
        )

    with session_scope(session_factory) as session:
        rows = session.query(ObservationRecord).all()

    assert len(rows) == 1
    assert rows[0].station == Station.GABRIEL_DE_CASTILLA
    assert rows[0].temperature_celsius == 1.4


def test_duplicate_station_and_observed_at_violates_unique_constraint(session_factory) -> None:
    observed_at = datetime(2024, 1, 15, 0, 0, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add(
            ObservationRecord(
                station=Station.GABRIEL_DE_CASTILLA,
                observed_at=observed_at,
                temperature_celsius=1.4,
                pressure_hpa=984.4,
                wind_speed_ms=7.1,
                is_good_quality=True,
            )
        )

    with pytest.raises(IntegrityError), session_scope(session_factory) as session:
        session.add(
            ObservationRecord(
                station=Station.GABRIEL_DE_CASTILLA,
                observed_at=observed_at,
                temperature_celsius=999.0,  # different value, same identity
                pressure_hpa=984.4,
                wind_speed_ms=7.1,
                is_good_quality=True,
            )
        )


def test_same_instant_different_station_is_not_a_duplicate(session_factory) -> None:
    observed_at = datetime(2024, 1, 15, 0, 0, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add(
            ObservationRecord(
                station=Station.GABRIEL_DE_CASTILLA,
                observed_at=observed_at,
                temperature_celsius=1.4,
                pressure_hpa=984.4,
                wind_speed_ms=7.1,
                is_good_quality=True,
            )
        )
        session.add(
            ObservationRecord(
                station=Station.JUAN_CARLOS_I,
                observed_at=observed_at,
                temperature_celsius=1.9,
                pressure_hpa=983.6,
                wind_speed_ms=2.6,
                is_good_quality=True,
            )
        )

    with session_scope(session_factory) as session:
        assert session.query(ObservationRecord).count() == 2


def test_session_scope_rolls_back_on_exception(session_factory) -> None:
    with pytest.raises(ValueError), session_scope(session_factory) as session:
        session.add(
            ObservationRecord(
                station=Station.GABRIEL_DE_CASTILLA,
                observed_at=datetime(2024, 1, 15, 0, 0, tzinfo=UTC),
                temperature_celsius=1.4,
                pressure_hpa=984.4,
                wind_speed_ms=7.1,
                is_good_quality=True,
            )
        )
        raise ValueError("simulated failure mid-transaction")

    with session_scope(session_factory) as session:
        assert session.query(ObservationRecord).count() == 0


def test_fetched_range_roundtrip(session_factory) -> None:
    with session_scope(session_factory) as session:
        session.add(
            FetchedRange(
                station=Station.GABRIEL_DE_CASTILLA,
                range_start=datetime(2024, 1, 1, tzinfo=UTC),
                range_end=datetime(2024, 1, 31, tzinfo=UTC),
            )
        )

    with session_scope(session_factory) as session:
        ranges = session.query(FetchedRange).all()

    assert len(ranges) == 1
    assert ranges[0].station == Station.GABRIEL_DE_CASTILLA
