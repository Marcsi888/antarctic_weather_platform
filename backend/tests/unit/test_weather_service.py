from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.db.repository import ObservationRepository
from app.db.session import create_sqlite_engine, make_session_factory
from app.domain.aggregation import AggregationLevel
from app.integrations.aemet.schemas import Station, StationObservation
from app.services.weather_service import WeatherService

UTC = ZoneInfo("UTC")


class FakeAemetClient:
    """Records calls and returns a fixed observation list, no HTTP involved."""

    def __init__(self, observations: list[StationObservation]) -> None:
        self._observations = observations
        self.call_count = 0
        self.requested_ranges: list[tuple[datetime, datetime]] = []

    async def get_observations(
        self, station: Station, start: datetime, end: datetime
    ) -> list[StationObservation]:
        self.call_count += 1
        self.requested_ranges.append((start, end))
        return self._observations


@pytest.fixture
def repository(tmp_path: Path) -> ObservationRepository:
    engine = create_sqlite_engine(tmp_path / "test.db")
    return ObservationRepository(make_session_factory(engine))


def _obs(hour: int) -> StationObservation:
    return StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2024, 1, 15, hour, tzinfo=UTC),
        temperature_celsius=1.0,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=True,
    )


async def test_cache_miss_calls_aemet_and_persists(repository: ObservationRepository) -> None:
    fake_client = FakeAemetClient([_obs(0), _obs(1)])
    service = WeatherService(fake_client, repository)
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)

    result = await service.get_observations(
        Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE
    )

    assert fake_client.call_count == 1
    assert len(result) == 2
    # Confirms the fetched data was actually persisted, not just returned.
    assert repository.is_range_cached(Station.GABRIEL_DE_CASTILLA, start, end) is True


async def test_cache_hit_does_not_call_aemet(repository: ObservationRepository) -> None:
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)
    repository.store_fetch_result(Station.GABRIEL_DE_CASTILLA, start, end, [_obs(0), _obs(1)])
    fake_client = FakeAemetClient([])

    service = WeatherService(fake_client, repository)
    result = await service.get_observations(
        Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE
    )

    assert fake_client.call_count == 0
    assert len(result) == 2


async def test_partial_overlap_is_a_miss_and_refetches_full_range(
    repository: ObservationRepository,
) -> None:
    # Matches the documented single-range-containment scope limit: a
    # smaller prior fetch does not satisfy a larger request.
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 15, 0, tzinfo=UTC),
        datetime(2024, 1, 15, 5, tzinfo=UTC),
        [_obs(0)],
    )
    fake_client = FakeAemetClient([_obs(0), _obs(10)])

    service = WeatherService(fake_client, repository)
    await service.get_observations(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 15, 0, tzinfo=UTC),
        datetime(2024, 1, 15, 23, tzinfo=UTC),
        AggregationLevel.NONE,
    )

    assert fake_client.call_count == 1


async def test_result_is_aggregated_per_requested_level(
    repository: ObservationRepository,
) -> None:
    fake_client = FakeAemetClient([_obs(0), _obs(1), _obs(2)])
    service = WeatherService(fake_client, repository)

    result = await service.get_observations(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 15, tzinfo=UTC),
        datetime(2024, 1, 16, tzinfo=UTC),
        AggregationLevel.DAILY,
    )

    assert len(result) == 1
    assert result[0].observation_count == 3


async def test_empty_aemet_response_persists_range_as_fetched(
    repository: ObservationRepository,
) -> None:
    fake_client = FakeAemetClient([])
    service = WeatherService(fake_client, repository)
    start = datetime(2024, 1, 15, tzinfo=UTC)
    end = datetime(2024, 1, 16, tzinfo=UTC)

    result = await service.get_observations(
        Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE
    )

    assert result == []
    # A second call for the same range must not hit AEMET again: the
    # empty result itself was cached via fetched_ranges.
    await service.get_observations(
        Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE
    )
    assert fake_client.call_count == 1


async def test_range_over_31_days_is_split_into_multiple_aemet_calls(
    repository: ObservationRepository,
) -> None:
    # AEMET rejects any single request spanning more than ~31 days
    # ("El rango de fechas no puede ser superior a 1 mes"), confirmed
    # live against the real API. A full-year request must become
    # multiple sub-31-day calls, not one oversized call.
    fake_client = FakeAemetClient([_obs(0)])
    service = WeatherService(fake_client, repository)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)

    await service.get_observations(Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE)

    assert fake_client.call_count > 1
    for chunk_start, chunk_end in fake_client.requested_ranges:
        assert (chunk_end - chunk_start).days <= 31


async def test_chunked_range_has_no_gaps_or_overlaps(
    repository: ObservationRepository,
) -> None:
    fake_client = FakeAemetClient([_obs(0)])
    service = WeatherService(fake_client, repository)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2025, 1, 1, tzinfo=UTC)

    await service.get_observations(Station.GABRIEL_DE_CASTILLA, start, end, AggregationLevel.NONE)

    ranges = fake_client.requested_ranges
    assert ranges[0][0] == start
    assert ranges[-1][1] == end
    for i in range(len(ranges) - 1):
        assert ranges[i][1] == ranges[i + 1][0]


async def test_range_under_31_days_is_a_single_aemet_call(
    repository: ObservationRepository,
) -> None:
    fake_client = FakeAemetClient([_obs(0)])
    service = WeatherService(fake_client, repository)

    await service.get_observations(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 15, tzinfo=UTC),
        AggregationLevel.NONE,
    )

    assert fake_client.call_count == 1


async def test_already_cached_chunk_within_a_large_range_is_not_refetched(
    repository: ObservationRepository,
) -> None:
    # A prior smaller fetch inside a later, larger request's span should
    # still yield a partial cache benefit: chunking must check the cache
    # per sub-range, not force a full re-fetch of everything.
    repository.store_fetch_result(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 2, 1, tzinfo=UTC),
        [_obs(0)],
    )
    fake_client = FakeAemetClient([_obs(0)])
    service = WeatherService(fake_client, repository)

    await service.get_observations(
        Station.GABRIEL_DE_CASTILLA,
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 3, 3, tzinfo=UTC),
        AggregationLevel.NONE,
    )

    # Only the second month-sized chunk should have required a real
    # AEMET call; the first was already cached.
    assert fake_client.call_count == 1
    assert fake_client.requested_ranges[0][0] == datetime(2024, 2, 1, tzinfo=UTC)
