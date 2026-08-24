from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.db.repository import ObservationRepository
from app.db.session import create_sqlite_engine, make_session_factory
from app.integrations.aemet.schemas import Station, StationObservation

UTC = ZoneInfo("UTC")


@pytest.fixture
def repository(tmp_path: Path) -> ObservationRepository:
    engine = create_sqlite_engine(tmp_path / "test.db")
    return ObservationRepository(make_session_factory(engine))


def _obs(hour: int, *, station: Station = Station.GABRIEL_DE_CASTILLA) -> StationObservation:
    return StationObservation(
        station=station,
        observed_at=datetime(2024, 1, 15, hour, 0, tzinfo=UTC),
        temperature_celsius=1.0 + hour,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=True,
    )


def test_is_range_cached_false_when_never_fetched(repository: ObservationRepository) -> None:
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)

    assert repository.is_range_cached(Station.GABRIEL_DE_CASTILLA, start, end) is False


def test_is_range_cached_true_for_exact_prior_fetch(repository: ObservationRepository) -> None:
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [])

    assert repository.is_range_cached(Station.GABRIEL_DE_CASTILLA, start, end) is True


def test_is_range_cached_true_for_sub_range_of_prior_fetch(
    repository: ObservationRepository,
) -> None:
    fetched_start = datetime(2024, 1, 1, tzinfo=UTC)
    fetched_end = datetime(2024, 1, 31, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, fetched_start, fetched_end, [])

    sub_start = datetime(2024, 1, 10, tzinfo=UTC)
    sub_end = datetime(2024, 1, 20, tzinfo=UTC)

    assert repository.is_range_cached(Station.GABRIEL_DE_CASTILLA, sub_start, sub_end) is True


def test_is_range_cached_false_when_range_extends_beyond_prior_fetch(
    repository: ObservationRepository,
) -> None:
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 10, tzinfo=UTC),
        datetime(2024, 1, 20, tzinfo=UTC),
        [],
    )

    # Requested range extends past the fetched range's end.
    requested_end = datetime(2024, 1, 25, tzinfo=UTC)

    assert (
        repository.is_range_cached(
            Station.GABRIEL_DE_CASTILLA, datetime(2024, 1, 10, tzinfo=UTC), requested_end
        )
        is False
    )


def test_is_range_cached_false_for_two_non_adjacent_fetches_not_merged(
    repository: ObservationRepository,
) -> None:
    # Deliberate scope limit: containment is checked against a single
    # stored range, not a union of multiple. Two separate fetches that
    # together would cover the request are still a miss.
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 10, tzinfo=UTC),
        [],
    )
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 15, tzinfo=UTC),
        datetime(2024, 1, 20, tzinfo=UTC),
        [],
    )

    assert (
        repository.is_range_cached(
            Station.GABRIEL_DE_CASTILLA,
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 20, tzinfo=UTC),
        )
        is False
    )


def test_is_range_cached_is_scoped_per_station(repository: ObservationRepository) -> None:
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [])

    assert repository.is_range_cached(Station.JUAN_CARLOS_I, start, end) is False


def test_store_and_retrieve_observations_roundtrip(repository: ObservationRepository) -> None:
    start = datetime(2024, 1, 15, 0, tzinfo=UTC)
    end = datetime(2024, 1, 15, 23, tzinfo=UTC)
    observations = [_obs(0), _obs(1), _obs(2)]

    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, observations)
    result = repository.get_observations(Station.GABRIEL_DE_CASTILLA, start, end)

    assert len(result) == 3
    assert result[0].observed_at == observations[0].observed_at


def test_get_observations_returns_raw_values_unfiltered_by_quality(
    repository: ObservationRepository,
) -> None:
    # The nulling-on-bad-quality policy lives in app.domain.aggregation,
    # not the repository: cached reads must return what was stored.
    bad_obs = StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2024, 1, 15, 0, tzinfo=UTC),
        temperature_celsius=999.0,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=False,
    )
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [bad_obs])

    result = repository.get_observations(Station.GABRIEL_DE_CASTILLA, start, end)

    assert result[0].temperature_celsius == 999.0
    assert result[0].is_good_quality is False


def test_get_observations_excludes_records_outside_range(
    repository: ObservationRepository,
) -> None:
    start = datetime(2024, 1, 15, 0, tzinfo=UTC)
    end = datetime(2024, 1, 15, 23, tzinfo=UTC)
    outside = StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2024, 1, 20, 0, tzinfo=UTC),
        temperature_celsius=1.0,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=True,
    )
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA, start, end + timedelta(days=10), [_obs(0), outside]
    )

    result = repository.get_observations(Station.GABRIEL_DE_CASTILLA, start, end)

    assert len(result) == 1


def test_store_fetch_result_is_idempotent_for_same_observation(
    repository: ObservationRepository,
) -> None:
    # Re-fetching a range that overlaps a previous fetch must not raise
    # on the unique constraint; store_fetch_result upserts via merge().
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [_obs(0)])
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [_obs(0)])

    result = repository.get_observations(Station.GABRIEL_DE_CASTILLA, start, end)

    assert len(result) == 1


def test_store_fetch_result_with_empty_observations_still_marks_range_fetched(
    repository: ObservationRepository,
) -> None:
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)

    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [])

    assert repository.is_range_cached(Station.GABRIEL_DE_CASTILLA, start, end) is True
    assert repository.get_observations(Station.GABRIEL_DE_CASTILLA, start, end) == []
