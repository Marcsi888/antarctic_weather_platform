import logging
from datetime import datetime
from typing import Protocol

from app.db.repository import ObservationRepository
from app.domain.aggregation import AggregatedObservation, AggregationLevel, aggregate
from app.integrations.aemet.schemas import Station, StationObservation

logger = logging.getLogger(__name__)


class AemetObservationSource(Protocol):
    """What WeatherService needs from an AEMET client — not the concrete
    AemetClient, so tests can substitute a fake with no real HTTP client,
    retry logic, or httpx dependency behind it at all.
    """

    async def get_observations(
        self, station: Station, start: datetime, end: datetime
    ) -> list[StationObservation]: ...


class WeatherService:
    """Orchestrates cache lookup, AEMET retrieval, and aggregation.

    Depends on AemetObservationSource and ObservationRepository through
    their constructors rather than constructing them itself, so tests can
    substitute fakes for both without any real HTTP call or database.
    Exceptions from either collaborator propagate unchanged — mapping
    them to HTTP responses is the API layer's responsibility, not this
    one's, which is why this class has no FastAPI dependency at all.
    """

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
        if self._repository.is_range_cached(station, start, end):
            logger.info("Cache hit for %s [%s, %s]", station.value, start, end)
        else:
            logger.info("Cache miss for %s [%s, %s], querying AEMET", station.value, start, end)
            fetched = await self._aemet_client.get_observations(station, start, end)
            self._repository.store_fetch_result(station, start, end, fetched)

        observations = self._repository.get_observations(station, start, end)
        return aggregate(observations, aggregation_level)
