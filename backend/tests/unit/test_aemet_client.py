from datetime import UTC, datetime

import httpx
import pytest
from pytest_httpx import HTTPXMock

from app.core.exceptions import (
    AemetAuthenticationError,
    AemetResponseError,
    AemetUnavailableError,
    UnknownStationError,
)
from app.integrations.aemet.client import AemetClient
from app.integrations.aemet.schemas import Station

BASE_URL = "https://opendata.aemet.es/opendata"
START = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
END = datetime(2024, 1, 15, 6, 0, 0, tzinfo=UTC)

DATOS_URL = "https://opendata.aemet.es/opendata/sh/fake-datos-id"


def _envelope_url(station: Station) -> str:
    return (
        f"{BASE_URL}/api/antartida/datos"
        f"/fechaini/2024-01-15T00:00:00UTC"
        f"/fechafin/2024-01-15T06:00:00UTC"
        f"/estacion/{station.value}"
    )


@pytest.fixture
def client() -> AemetClient:
    http_client = httpx.AsyncClient(timeout=10.0)
    return AemetClient(
        http_client=http_client,
        api_key="test-key",
        base_url=BASE_URL,
        retry_delay_seconds=0,
    )


async def test_get_observations_success(client: AemetClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={
            "descripcion": "exito",
            "estado": 200,
            "datos": DATOS_URL,
            "metadatos": "https://opendata.aemet.es/opendata/sh/fake-metadatos-id",
        },
    )
    httpx_mock.add_response(
        url=DATOS_URL,
        json=[
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T00:00:00Z",
                "temp": 1.4,
                "pres": 984.4,
                "vel": 7.1,
                "qdato": 0.0,
            }
        ],
    )

    observations = await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)

    assert len(observations) == 1
    assert observations[0].station is Station.GABRIEL_DE_CASTILLA
    assert observations[0].temperature_celsius == 1.4


async def test_get_observations_api_key_sent_only_on_envelope_request(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
        match_headers={"api_key": "test-key"},
    )
    httpx_mock.add_response(url=DATOS_URL, json=[])

    await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)

    requests = httpx_mock.get_requests()
    assert "api_key" not in requests[1].headers


async def test_get_observations_404_returns_empty_list(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        status_code=404,
        json={"descripcion": "No hay datos", "estado": 404},
    )

    observations = await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)

    assert observations == []


async def test_get_observations_401_raises_authentication_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_envelope_url(Station.GABRIEL_DE_CASTILLA), status_code=401)

    with pytest.raises(AemetAuthenticationError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_429_raises_unavailable_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_envelope_url(Station.GABRIEL_DE_CASTILLA), status_code=429)

    with pytest.raises(AemetUnavailableError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_retries_once_on_500_then_succeeds(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_envelope_url(Station.GABRIEL_DE_CASTILLA), status_code=500)
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
    )
    httpx_mock.add_response(url=DATOS_URL, json=[])

    observations = await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)

    assert observations == []
    assert len(httpx_mock.get_requests()) == 3


async def test_get_observations_persistent_500_raises_after_retry(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_envelope_url(Station.GABRIEL_DE_CASTILLA), status_code=500)
    httpx_mock.add_response(url=_envelope_url(Station.GABRIEL_DE_CASTILLA), status_code=500)

    with pytest.raises(AemetUnavailableError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_malformed_envelope_json_raises_response_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        content=b"not json",
        headers={"content-type": "application/json"},
    )

    with pytest.raises(AemetResponseError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_envelope_missing_field_raises_response_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200},  # missing datos/metadatos
    )

    with pytest.raises(AemetResponseError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_datos_not_a_list_raises_response_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
    )
    httpx_mock.add_response(url=DATOS_URL, json={"unexpected": "object"})

    with pytest.raises(AemetResponseError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_record_missing_required_field_raises_response_error(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
    )
    httpx_mock.add_response(url=DATOS_URL, json=[{"temp": 1.0}])  # no identificacion/fhora

    with pytest.raises(AemetResponseError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_unknown_station_identifier_raises(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
    )
    httpx_mock.add_response(
        url=DATOS_URL,
        json=[
            {
                "identificacion": "99999",
                "fhora": "2024-01-15T00:00:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 5.0,
            }
        ],
    )

    with pytest.raises(UnknownStationError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


async def test_get_observations_timeout_raises_unavailable_after_retry(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(httpx.ConnectTimeout("connection timed out"))
    httpx_mock.add_exception(httpx.ConnectTimeout("connection timed out"))

    with pytest.raises(AemetUnavailableError):
        await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)


def test_default_retry_delay_is_nonzero() -> None:
    # Confirms the test fixture's retry_delay_seconds=0 override is a
    # test-only convenience, not a change to the production default.
    http_client = httpx.AsyncClient(timeout=10.0)
    default_client = AemetClient(http_client=http_client, api_key="k", base_url=BASE_URL)

    assert default_client._retry_delay_seconds > 0


async def test_get_observations_datetime_formatted_with_utc_suffix(
    client: AemetClient, httpx_mock: HTTPXMock
) -> None:
    # AEMET's documented request format is AAAA-MM-DDTHH:MM:SSUTC, distinct
    # from the Z-suffixed ISO 8601 format it uses in *responses*.
    httpx_mock.add_response(
        url=_envelope_url(Station.GABRIEL_DE_CASTILLA),
        json={"descripcion": "exito", "estado": 200, "datos": DATOS_URL, "metadatos": "x"},
    )
    httpx_mock.add_response(url=DATOS_URL, json=[])

    await client.get_observations(Station.GABRIEL_DE_CASTILLA, START, END)

    request_url = str(httpx_mock.get_requests()[0].url)
    assert "2024-01-15T00:00:00UTC" in request_url
    assert "2024-01-15T06:00:00UTC" in request_url
