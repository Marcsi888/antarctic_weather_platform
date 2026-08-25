import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from app.core.config import get_settings

DATOS_URL = "https://opendata.aemet.es/opendata/sh/fake-datos-id"
_ENVELOPE_URL_PATTERN = re.compile(r"https://opendata\.aemet\.es/opendata/api/antartida/datos/.*")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("AEMET_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()


def _mock_aemet_success(httpx_mock: HTTPXMock, records: list[dict[str, object]]) -> None:
    httpx_mock.add_response(
        url=_ENVELOPE_URL_PATTERN,
        json={
            "descripcion": "exito",
            "estado": 200,
            "datos": DATOS_URL,
            "metadatos": "https://opendata.aemet.es/opendata/sh/fake-metadatos-id",
        },
    )
    httpx_mock.add_response(url=DATOS_URL, json=records)


def test_valid_request_returns_observations(client: TestClient, httpx_mock: HTTPXMock) -> None:
    _mock_aemet_success(
        httpx_mock,
        [
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

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
            "timezone": "UTC",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["temperature_celsius"] == 1.4
    assert body[0]["pressure_hpa"] == 984.4
    assert body[0]["wind_speed_ms"] == 7.1


def test_invalid_station_returns_400(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={
            "station": "not_a_real_station",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
        },
    )

    assert response.status_code == 400


def test_start_after_end_returns_400(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T10:00:00",
            "end": "2024-01-15T09:00:00",
        },
    )

    assert response.status_code == 400


def test_malformed_datetime_returns_400(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "not-a-date",
            "end": "2024-01-15T09:00:00",
        },
    )

    assert response.status_code == 400


def test_offset_bearing_datetime_rejected(client: TestClient) -> None:
    # The brief's required input format has no offset; the timezone is
    # supplied separately. An offset-bearing string must not be silently
    # accepted as if it were the documented format.
    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00+02:00",
            "end": "2024-01-15T01:00:00",
        },
    )

    assert response.status_code == 400


def test_invalid_timezone_returns_400(client: TestClient) -> None:
    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
            "timezone": "Not/A_Real_Zone",
        },
    )

    assert response.status_code == 400


def test_missing_required_param_returns_422(client: TestClient) -> None:
    # FastAPI's own required-param validation, distinct from our domain
    # validation (400) — this is Pydantic/FastAPI rejecting the request
    # before it ever reaches our code.
    response = client.get("/observations", params={"start": "2024-01-15T00:00:00"})

    assert response.status_code == 422


def test_zero_measurements_returns_all_three(client: TestClient, httpx_mock: HTTPXMock) -> None:
    _mock_aemet_success(
        httpx_mock,
        [
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

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
            "timezone": "UTC",
        },
    )

    body = response.json()[0]
    assert body["temperature_celsius"] is not None
    assert body["pressure_hpa"] is not None
    assert body["wind_speed_ms"] is not None
    assert body["wind_speed_max_ms"] is not None


def test_single_measurement_selection_nulls_the_others(
    client: TestClient, httpx_mock: HTTPXMock
) -> None:
    _mock_aemet_success(
        httpx_mock,
        [
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

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
            "timezone": "UTC",
            "measurement": "temperature",
        },
    )

    body = response.json()[0]
    assert body["temperature_celsius"] == 1.4
    assert body["pressure_hpa"] is None
    assert body["wind_speed_ms"] is None
    assert body["wind_speed_max_ms"] is None


def test_wind_speed_max_reflects_gust_hidden_by_the_mean(
    client: TestClient, httpx_mock: HTTPXMock
) -> None:
    # Confirmed with the assigning team: turbine operation has minimum,
    # maximum, and optimal wind-speed thresholds, so a mean alone can
    # conceal a gust relevant to a wind-farm feasibility assessment.
    _mock_aemet_success(
        httpx_mock,
        [
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T00:00:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 4.0,
                "qdato": 0.0,
            },
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T00:10:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 14.0,
                "qdato": 0.0,
            },
        ],
    )

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T01:00:00",
            "timezone": "UTC",
            "aggregation": "hourly",
        },
    )

    body = response.json()[0]
    assert body["wind_speed_ms"] == 9.0
    assert body["wind_speed_max_ms"] == 14.0


def test_second_request_for_same_range_does_not_call_aemet_again(
    client: TestClient, httpx_mock: HTTPXMock
) -> None:
    _mock_aemet_success(httpx_mock, [])
    params = {
        "station": "gabriel_de_castilla",
        "start": "2024-01-15T00:00:00",
        "end": "2024-01-15T01:00:00",
        "timezone": "UTC",
    }

    first = client.get("/observations", params=params)
    second = client.get("/observations", params=params)

    assert first.status_code == 200
    assert second.status_code == 200
    # pytest_httpx raises if a registered response goes unconsumed, and
    # would raise here too if the second call issued unexpected requests;
    # explicitly confirm only the first call's two AEMET requests happened.
    assert len(httpx_mock.get_requests()) == 2


def test_daily_aggregation_returns_bucketed_result(
    client: TestClient, httpx_mock: HTTPXMock
) -> None:
    _mock_aemet_success(
        httpx_mock,
        [
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T00:00:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 5.0,
                "qdato": 0.0,
            },
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T12:00:00Z",
                "temp": 3.0,
                "pres": 980.0,
                "vel": 5.0,
                "qdato": 0.0,
            },
        ],
    )

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T23:00:00",
            "timezone": "UTC",
            "aggregation": "daily",
        },
    )

    body = response.json()
    assert len(body) == 1
    assert body[0]["temperature_celsius"] == 2.0
    assert body[0]["observation_count"] == 2


def test_response_datetime_is_europe_madrid_with_offset(
    client: TestClient, httpx_mock: HTTPXMock
) -> None:
    _mock_aemet_success(
        httpx_mock,
        [
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T13:00:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 5.0,
                "qdato": 0.0,
            }
        ],
    )

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T23:00:00",
            "timezone": "UTC",
        },
    )

    assert response.json()[0]["datetime"] == "2024-01-15T14:00:00+01:00"


def test_utc_offset_timezone_form_is_accepted(client: TestClient, httpx_mock: HTTPXMock) -> None:
    # The challenge spec offers a raw UTC offset (e.g. "+02:00") as an
    # alternative to naming an IANA timezone.
    _mock_aemet_success(
        httpx_mock,
        [
            {
                "identificacion": "89070",
                "fhora": "2024-01-15T12:00:00Z",
                "temp": 1.0,
                "pres": 980.0,
                "vel": 5.0,
                "qdato": 0.0,
            }
        ],
    )

    response = client.get(
        "/observations",
        params={
            "station": "gabriel_de_castilla",
            "start": "2024-01-15T00:00:00",
            "end": "2024-01-15T23:00:00",
            "timezone": "+02:00",
        },
    )

    assert response.status_code == 200
    # 12:00 UTC displayed in Europe/Madrid (winter, +01:00), regardless of
    # the +02:00 input timezone — output is unconditionally Madrid.
    assert response.json()[0]["datetime"] == "2024-01-15T13:00:00+01:00"
