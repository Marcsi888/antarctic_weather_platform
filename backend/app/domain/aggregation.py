from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.domain.time import to_output_representation
from app.integrations.aemet.schemas import StationObservation


class AggregationLevel(Enum):
    NONE = "none"
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class AggregatedObservation(BaseModel):
    """One summarized bucket. bucket_start is always Europe/Madrid."""

    model_config = ConfigDict(frozen=True)

    bucket_start: datetime
    temperature_celsius: float | None
    pressure_hpa: float | None
    wind_speed_ms: float | None
    observation_count: int


# The bucket key is the local (Europe/Madrid) calendar tuple truncated to
# the aggregation level's resolution, not a UTC timestamp
_BucketKey = tuple[int, int, int, int] | tuple[int, int, int] | tuple[int, int]


def _bucket_key(local_dt: datetime, level: AggregationLevel) -> _BucketKey:
    if level is AggregationLevel.HOURLY:
        return (local_dt.year, local_dt.month, local_dt.day, local_dt.hour)
    if level is AggregationLevel.DAILY:
        return (local_dt.year, local_dt.month, local_dt.day)
    if level is AggregationLevel.MONTHLY:
        return (local_dt.year, local_dt.month)
    raise ValueError(f"_bucket_key is not defined for {level}")


def _bucket_start(key: _BucketKey, local_dt: datetime) -> datetime:
    if len(key) == 4:
        return local_dt.replace(minute=0, second=0, microsecond=0)
    if len(key) == 3:
        return local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _mean(values: Iterable[float]) -> float | None:
    values = list(values)
    if not values:
        return None
    return sum(values) / len(values)


def aggregate(
    observations: list[StationObservation], level: AggregationLevel
) -> list[AggregatedObservation]:
    if level is AggregationLevel.NONE:
        return [
            AggregatedObservation(
                bucket_start=to_output_representation(obs.observed_at),
                temperature_celsius=obs.temperature_celsius if obs.is_good_quality else None,
                pressure_hpa=obs.pressure_hpa if obs.is_good_quality else None,
                wind_speed_ms=obs.wind_speed_ms if obs.is_good_quality else None,
                observation_count=1,
            )
            for obs in observations
        ]

    buckets: dict[_BucketKey, list[StationObservation]] = defaultdict(list)
    bucket_starts: dict[_BucketKey, datetime] = {}

    for obs in observations:
        local_dt = to_output_representation(obs.observed_at)
        key = _bucket_key(local_dt, level)
        buckets[key].append(obs)
        bucket_starts.setdefault(key, _bucket_start(key, local_dt))

    results = [
        AggregatedObservation(
            bucket_start=bucket_starts[key],
            temperature_celsius=_mean(
                obs.temperature_celsius
                for obs in bucket_observations
                if obs.is_good_quality and obs.temperature_celsius is not None
            ),
            pressure_hpa=_mean(
                obs.pressure_hpa
                for obs in bucket_observations
                if obs.is_good_quality and obs.pressure_hpa is not None
            ),
            wind_speed_ms=_mean(
                obs.wind_speed_ms
                for obs in bucket_observations
                if obs.is_good_quality and obs.wind_speed_ms is not None
            ),
            observation_count=len(bucket_observations),
        )
        for key, bucket_observations in buckets.items()
    ]
    return sorted(results, key=lambda r: r.bucket_start)
