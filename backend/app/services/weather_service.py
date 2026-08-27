import logging
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from app.db.repository import ObservationRepository
from app.domain.aggregation import AggregatedObservation, AggregationLevel, aggregate
from app.integrations.aemet.schemas import Station, StationObservation

logger = logging.getLogger(__name__)

# AEMET has no "latest available date" endpoint at all — it is a pure
# range-query API. The probe fallback below steps back through recent
# windows looking for the first one with data; bounded so a station with
# no AEMET coverage at all (shouldn't happen in practice, but must not
# hang) fails after a fixed number of attempts rather than looping
# forever.
_PROBE_WINDOW = timedelta(days=60)
_MAX_PROBE_ATTEMPTS = 6

# "Latest available date" changes at most roughly monthly in reality
# (see WeatherService docs), so a short TTL avoids a live AEMET probe on
# every frontend page load without risking meaningfully stale answers.
_LATEST_AVAILABLE_TTL_SECONDS = 3600.0

# AEMET rejects any request spanning more than ~31 days, confirmed
# empirically ("El rango de fechas no puede ser superior a 1 mes"). Not
# documented anywhere; discovered by a real query over a full year
# returning far fewer observations than it should have, silently, rather
# than an error — see AemetRangeTooLongError. 31 rather than 30: a
# request from the 1st to the 1st of the following month (a true calendar
# month) is exactly 31 days for the longest months and was confirmed to
# succeed; 32 days was confirmed to fail.
_MAX_AEMET_RANGE = timedelta(days=31)


def _chunk_range(start: datetime, end: datetime) -> Iterator[tuple[datetime, datetime]]:
    current = start
    while current < end:
        chunk_end = min(current + _MAX_AEMET_RANGE, end)
        yield current, chunk_end
        current = chunk_end


class AemetObservationSource(Protocol):
    """The subset of AemetClient this service needs, lets tests substitute a fake with no real HTTP client behind it."""

    async def get_observations(
        self, station: Station, start: datetime, end: datetime
    ) -> list[StationObservation]: ...


class WeatherService:
    """Orchestrates cache lookup, AEMET retrieval, and aggregation."""

    # Exceptions from either collaborator propagate unchanged; mapping
    # them to HTTP responses is the API layer's job, not this one's.
    def __init__(
        self, aemet_client: AemetObservationSource, repository: ObservationRepository
    ) -> None:
        self._aemet_client = aemet_client
        self._repository = repository
        # station -> (result, cached_at_monotonic). A plain dict is
        # sufficient: one process, a handful of stations, no eviction
        # policy needed beyond the TTL check itself.
        self._latest_available_cache: dict[Station, tuple[date | None, float]] = {}

    async def get_observations(
        self,
        station: Station,
        start: datetime,
        end: datetime,
        aggregation_level: AggregationLevel,
    ) -> list[AggregatedObservation]:
        # AEMET rejects requests over ~31 days, so the requested range is
        # split into sub-ranges before ever reaching the client. Each
        # sub-range is checked against the cache independently: a later
        # request overlapping only part of a previously-fetched year
        # should still get a partial cache benefit, not force a full
        # re-fetch of the whole thing.
        for chunk_start, chunk_end in _chunk_range(start, end):
            if self._repository.is_range_cached(station, chunk_start, chunk_end):
                logger.info("Cache hit for %s [%s, %s]", station.value, chunk_start, chunk_end)
                continue

            logger.info(
                "Cache miss for %s [%s, %s], querying AEMET",
                station.value,
                chunk_start,
                chunk_end,
            )
            fetched = await self._aemet_client.get_observations(station, chunk_start, chunk_end)
            self._repository.store_fetch_result(station, chunk_start, chunk_end, fetched)

        observations = self._repository.get_observations(station, start, end)
        return aggregate(observations, aggregation_level)

    async def get_latest_available_date(self, station: Station) -> date | None:
        """The most recent date AEMET is confirmed to have data for, or None if unknown.

        Cache-first: the local SQLite cache is already the most
        authoritative record this app has of "what data have we actually
        confirmed exists," since it is populated entirely by successful
        AEMET fetches. A live AEMET probe only runs as a cold-start
        fallback (an empty or freshly-created database), not on the
        common path.
        """
        cached = self._latest_available_cache.get(station)
        if cached is not None:
            result, cached_at = cached
            if time.monotonic() - cached_at < _LATEST_AVAILABLE_TTL_SECONDS:
                return result

        latest_observed_at = self._repository.get_latest_observed_at(station)
        if latest_observed_at is not None:
            result = latest_observed_at.date()
            self._latest_available_cache[station] = (result, time.monotonic())
            return result

        result = await self._probe_aemet_for_latest_date(station)
        self._latest_available_cache[station] = (result, time.monotonic())
        return result

    async def _probe_aemet_for_latest_date(self, station: Station) -> date | None:
        window_end = datetime.now(UTC)
        for _ in range(_MAX_PROBE_ATTEMPTS):
            window_start = window_end - _PROBE_WINDOW
            observations = await self._aemet_client.get_observations(
                station, window_start, window_end
            )
            if observations:
                return max(obs.observed_at for obs in observations).date()
            window_end = window_start
        logger.warning(
            "No AEMET data found for %s after %d probe attempts", station.value, _MAX_PROBE_ATTEMPTS
        )
        return None
