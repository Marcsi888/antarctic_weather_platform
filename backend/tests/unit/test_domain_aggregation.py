from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.aggregation import AggregationLevel, aggregate
from app.integrations.aemet.schemas import Station, StationObservation

UTC = ZoneInfo("UTC")


def _obs(
    hour: int,
    minute: int,
    *,
    day: int = 15,
    month: int = 1,
    temp: float | None = 1.0,
    good: bool = True,
) -> StationObservation:
    return StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2026, month, day, hour, minute, tzinfo=UTC),
        temperature_celsius=temp,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=good,
    )


def test_none_aggregation_passes_through_one_bucket_per_observation() -> None:
    observations = [_obs(0, 0), _obs(0, 10), _obs(0, 20)]

    result = aggregate(observations, AggregationLevel.NONE)

    assert len(result) == 3
    assert all(r.observation_count == 1 for r in result)


def test_none_aggregation_nulls_bad_quality_measurement() -> None:
    observations = [_obs(0, 0, temp=99.0, good=False)]

    result = aggregate(observations, AggregationLevel.NONE)

    assert result[0].temperature_celsius is None


def test_hourly_aggregation_groups_within_the_hour() -> None:
    # 13:00 UTC winter -> 14:00 Madrid; all three fall in the same local hour.
    observations = [_obs(13, 0, temp=1.0), _obs(13, 10, temp=2.0), _obs(13, 50, temp=3.0)]

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert len(result) == 1
    assert result[0].observation_count == 3
    assert result[0].temperature_celsius == 2.0  # mean of 1, 2, 3


def test_hourly_aggregation_splits_across_hour_boundary() -> None:
    observations = [_obs(13, 59), _obs(14, 0)]

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert len(result) == 2


def test_daily_aggregation_uses_madrid_calendar_day_not_utc() -> None:
    # 23:30 UTC on Jan 15 is 00:30 Madrid on Jan 16 (winter, +01:00).
    # A UTC-based bucketing would incorrectly group this with Jan 15.
    late_utc = _obs(23, 30, day=15, temp=10.0)
    early_next_utc = _obs(0, 30, day=16, temp=20.0)

    result = aggregate([late_utc, early_next_utc], AggregationLevel.DAILY)

    assert len(result) == 1
    assert result[0].bucket_start.date().isoformat() == "2026-01-16"
    assert result[0].temperature_celsius == 15.0


def test_daily_aggregation_bucket_spans_dst_spring_forward_transition() -> None:
    # 2026-03-29: Madrid spring-forward. Both instants land on the same
    # Madrid calendar day (March 29) despite the 1-hour UTC offset shift
    # happening between them.
    before_transition = StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2026, 3, 29, 0, 30, tzinfo=UTC),  # 01:30 Madrid (+01:00)
        temperature_celsius=1.0,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=True,
    )
    after_transition = StationObservation(
        station=Station.GABRIEL_DE_CASTILLA,
        observed_at=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),  # 14:00 Madrid (+02:00)
        temperature_celsius=3.0,
        pressure_hpa=980.0,
        wind_speed_ms=5.0,
        is_good_quality=True,
    )

    result = aggregate([before_transition, after_transition], AggregationLevel.DAILY)

    assert len(result) == 1
    assert result[0].bucket_start.date().isoformat() == "2026-03-29"
    assert result[0].observation_count == 2


def test_monthly_aggregation_groups_by_madrid_month() -> None:
    observations = [_obs(12, 0, day=1, month=1), _obs(12, 0, day=31, month=1)]

    result = aggregate(observations, AggregationLevel.MONTHLY)

    assert len(result) == 1
    assert result[0].bucket_start.month == 1
    assert result[0].bucket_start.day == 1


def test_aggregation_excludes_bad_quality_readings_from_mean() -> None:
    observations = [
        _obs(13, 0, temp=10.0, good=True),
        _obs(13, 10, temp=1000.0, good=False),  # sensor fault, flagged
        _obs(13, 20, temp=20.0, good=True),
    ]

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert result[0].temperature_celsius == 15.0  # mean of 10, 20 only
    assert result[0].observation_count == 3  # bucket still counts all readings


def test_aggregation_bucket_all_bad_quality_yields_none_not_zero() -> None:
    observations = [_obs(13, 0, temp=5.0, good=False), _obs(13, 10, temp=6.0, good=False)]

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert result[0].temperature_celsius is None
    assert result[0].observation_count == 2


def test_aggregation_bucket_all_missing_measurement_yields_none() -> None:
    observations = [_obs(13, 0, temp=None), _obs(13, 10, temp=None)]

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert result[0].temperature_celsius is None


def test_aggregation_results_are_sorted_by_bucket_start() -> None:
    observations = [_obs(15, 0), _obs(13, 0), _obs(14, 0)]

    result = aggregate(observations, AggregationLevel.HOURLY)

    starts = [r.bucket_start for r in result]
    assert starts == sorted(starts)


def test_aggregation_bucket_start_is_europe_madrid() -> None:
    observations = [_obs(13, 0)]  # 14:00 Madrid winter

    result = aggregate(observations, AggregationLevel.HOURLY)

    assert result[0].bucket_start.isoformat() == "2026-01-15T14:00:00+01:00"


def test_empty_observation_list_returns_empty_result() -> None:
    assert aggregate([], AggregationLevel.HOURLY) == []
    assert aggregate([], AggregationLevel.NONE) == []
