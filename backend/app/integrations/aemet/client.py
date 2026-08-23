import asyncio
import logging
from datetime import datetime

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    AemetAuthenticationError,
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


class AemetClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        base_url: str,
        retry_delay_seconds: float = _RETRY_DELAY_SECONDS,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._retry_delay_seconds = retry_delay_seconds

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
            response = await self._http_client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError):
            logger.warning("AEMET request timed out or failed to connect, retrying once: %s", url)
            await asyncio.sleep(self._retry_delay_seconds)
            try:
                response = await self._http_client.get(url, headers=headers)
            except (httpx.TimeoutException, httpx.ConnectError) as retry_exc:
                raise AemetUnavailableError(
                    "AEMET did not respond after retry"
                ) from retry_exc
            return response

        if response.status_code in _RETRYABLE_STATUS_CODES:
            logger.warning(
                "AEMET returned %s, retrying once: %s", response.status_code, url
            )
            await asyncio.sleep(self._retry_delay_seconds)
            response = await self._http_client.get(url, headers=headers)

        return response

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

    def _parse_envelope(self, response: httpx.Response) -> AemetEnvelope:
        try:
            body = response.json()
        except ValueError as exc:
            raise AemetResponseError("AEMET envelope response was not valid JSON") from exc

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
