import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Protocol

from app.db.repository import ObservationRepository
from app.domain.aggregation import AggregatedObservation, AggregationLevel, aggregate
from app.integrations.aemet.schemas import Station, StationObservation

logger = logging.getLogger(__name__)

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
