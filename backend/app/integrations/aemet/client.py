import asyncio
import logging
import time
from datetime import datetime

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    AemetAuthenticationError,
    AemetRangeTooLongError,
    AemetResponseError,
    AemetUnavailableError,
    UnknownStationError,
)
from app.integrations.aemet.schemas import (
    AemetEnvelope,
    AemetObservationDTO,
    Station,
    StationObservation,
    map_to_observation,
)

logger = logging.getLogger(__name__)

_AEMET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SUTC"

# One retry, short fixed delay: this is a single-user local application,
# not a distributed system under load, so the failure this guards against
# is "the network blipped," not "the upstream is overloaded and needs
# backoff pressure." A second attempt either succeeds quickly or the
# caller learns AEMET is genuinely unavailable.
_RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
_RETRY_DELAY_SECONDS = 1.0

# AEMET does not publish a rate limit. Per guidance from the assigning
# team, the correct response to an undocumented limit is to be
# conservative rather than to guess a threshold and tune against it: a
# minimum spacing between outbound requests, applied here rather than
# left to callers, so every caller of this client benefits regardless of
# how many are issuing requests concurrently.
_MIN_REQUEST_INTERVAL_SECONDS = 0.5

# A real 429 is direct evidence we are too close to whatever AEMET's
# actual limit is; the cooldown after one is longer than the baseline
# spacing, on the reasoning that a single documented signal about the
# real limit is worth more than the conservative default guess.
_RATE_LIMIT_COOLDOWN_SECONDS = 5.0


class AemetClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        retry_delay_seconds: float = _RETRY_DELAY_SECONDS,
        min_request_interval_seconds: float = _MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._retry_delay_seconds = retry_delay_seconds
        self._min_request_interval_seconds = min_request_interval_seconds
        # Guards _next_allowed_time so concurrent callers cannot both
        # observe "enough time has passed" and fire simultaneously; an
        # unsynchronized check-then-sleep would let exactly that race
        # defeat the throttle under concurrent use.
        self._throttle_lock = asyncio.Lock()
        self._next_allowed_time = 0.0

    async def get_observations(
        self, station: Station, start: datetime, end: datetime
    ) -> list[StationObservation]:
        envelope = await self._request_envelope(station, start, end)
        if envelope is None:
            # AEMET's 404 for an empty range is expected, not exceptional:
            # the Antarctic dataset is updated annually, so recent ranges
            # routinely have no data yet.
            return []

        records = await self._request_records(envelope.datos)
        return self._parse_records(records)

    async def _request_envelope(
        self, station: Station, start: datetime, end: datetime
    ) -> AemetEnvelope | None:
        url = (
            f"{self._base_url}/api/antartida/datos"
            f"/fechaini/{self._format_datetime(start)}"
            f"/fechafin/{self._format_datetime(end)}"
            f"/estacion/{station.value}"
        )
        response = await self._get_with_retry(url, headers={"api_key": self._api_key})

        if response.status_code == 404:
            return None
        self._raise_for_unexpected_status(response)

        return self._parse_envelope(response)

    async def _request_records(self, datos_url: str) -> list[dict[str, object]]:
        # The datos URL is a pre-signed, time-limited link AEMET issues in
        # the envelope response; it does not take the api_key header.
        response = await self._get_with_retry(datos_url, headers=None)
        self._raise_for_unexpected_status(response)

        try:
            body = response.json()
        except ValueError as exc:
            raise AemetResponseError("AEMET observation payload was not valid JSON") from exc

        if not isinstance(body, list):
            raise AemetResponseError(
                f"Expected a JSON array of observations, got {type(body).__name__}"
            )
        return body

    async def _get_with_retry(
        self, url: str, *, headers: dict[str, str] | None
    ) -> httpx.Response:
        try:
            response = await self._throttled_get(url, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning("AEMET request timed out or failed to connect, retrying once: %s", url)
            await asyncio.sleep(self._retry_delay_seconds)
            try:
                response = await self._throttled_get(url, headers=headers)
            except (httpx.TimeoutException, httpx.ConnectError) as retry_exc:
                raise AemetUnavailableError(
                    "AEMET did not respond after retry"
                ) from retry_exc
            return response

        if response.status_code == 429:
            self._apply_rate_limit_cooldown()
        elif response.status_code in _RETRYABLE_STATUS_CODES:
            logger.warning(
                "AEMET returned %s, retrying once: %s", response.status_code, url
            )
            await asyncio.sleep(self._retry_delay_seconds)
            response = await self._throttled_get(url, headers=headers)

        return response

    async def _throttled_get(
        self, url: str, *, headers: dict[str, str] | None
    ) -> httpx.Response:
        async with self._throttle_lock:
            wait_seconds = self._next_allowed_time - time.monotonic()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._next_allowed_time = time.monotonic() + self._min_request_interval_seconds
        return await self._http_client.get(url, headers=headers)

    def _apply_rate_limit_cooldown(self) -> None:
        logger.warning(
            "AEMET returned 429; applying a %.1fs cooldown before further requests",
            _RATE_LIMIT_COOLDOWN_SECONDS,
        )
        self._next_allowed_time = time.monotonic() + _RATE_LIMIT_COOLDOWN_SECONDS

    def _raise_for_unexpected_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise AemetAuthenticationError(
                f"AEMET rejected the API key (status {response.status_code})"
            )
        if response.status_code == 429:
            raise AemetUnavailableError("AEMET rate limit exceeded (429)")
        if response.status_code >= 500:
            raise AemetUnavailableError(
                f"AEMET returned server error {response.status_code}"
            )
        if response.status_code >= 400:
            raise AemetResponseError(
                f"AEMET returned unexpected status {response.status_code}"
            )

    def _parse_envelope(self, response: httpx.Response) -> AemetEnvelope | None:
        try:
            body = response.json()
        except ValueError as exc:
            raise AemetResponseError("AEMET envelope response was not valid JSON") from exc

        # AEMET signals "no data for this range" two different ways,
        # confirmed live: a genuine HTTP 404 (handled by the caller before
        # this method runs), and an HTTP 200 whose body carries
        # estado: 404 with no datos/metadatos fields at all. The same
        # estado: 404 wrapper is also used for a range exceeding AEMET's
        # undocumented ~31-day limit ("El rango de fechas no puede ser
        # superior a 1 mes") — a rejected request, not an empty result —
        # distinguished only by the descripcion text, since AEMET gives
        # no separate status code for it.
        if isinstance(body, dict) and body.get("estado") == 404:
            descripcion = body.get("descripcion", "")
            if isinstance(descripcion, str) and "rango de fechas" in descripcion.lower():
                raise AemetRangeTooLongError(descripcion)
            return None

        try:
            return AemetEnvelope.model_validate(body)
        except PydanticValidationError as exc:
            raise AemetResponseError(
                f"AEMET envelope response was missing expected fields: {exc}"
            ) from exc

    def _parse_records(self, records: list[dict[str, object]]) -> list[StationObservation]:
        observations = []
        for record in records:
            try:
                dto = AemetObservationDTO.model_validate(record)
            except PydanticValidationError as exc:
                raise AemetResponseError(
                    f"AEMET observation record was missing expected fields: {exc}"
                ) from exc

            try:
                observations.append(map_to_observation(dto))
            except ValueError as exc:
                raise UnknownStationError(dto.identificacion) from exc

        return observations

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.strftime(_AEMET_DATETIME_FORMAT)
