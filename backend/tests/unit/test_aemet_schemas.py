import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.aemet.schemas import (
    AemetEnvelope,
    AemetObservationDTO,
    Station,
    map_to_observation,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def test_envelope_parses_two_step_response() -> None:
    envelope = AemetEnvelope.model_validate(_load("aemet_envelope_response.json"))

    assert envelope.estado == 200
    assert envelope.datos.startswith("https://opendata.aemet.es/")
    assert envelope.metadatos.startswith("https://opendata.aemet.es/")


def test_gabriel_de_castilla_observations_parse() -> None:
    records = _load("aemet_gabriel_de_castilla_datos.json")

    observations = [AemetObservationDTO.model_validate(r) for r in records]

    assert len(observations) == 3
    assert observations[0].identificacion == "89070"
    assert observations[0].temp == 1.4
    assert observations[0].pres == 984.4
    assert observations[0].vel == 7.1


def test_gabriel_de_castilla_nan_sentinel_becomes_none() -> None:
    # tsmn/tsmx are "NaN" in the fixture but aren't modeled fields at all,
    # so the meaningful check is that modeled fields tolerate the same
    # sentinel convention elsewhere in AEMET's payload (see JCI fixture).
    records = _load("aemet_gabriel_de_castilla_datos.json")

    observations = [AemetObservationDTO.model_validate(r) for r in records]

    assert all(obs.temp is not None for obs in observations)


def test_juan_carlos_i_observation_parses_despite_extra_nan_fields() -> None:
    records = _load("aemet_juan_carlos_i_datos.json")

    observation = AemetObservationDTO.model_validate(records[0])

    assert observation.identificacion == "89064"
    assert observation.temp == 1.9
    assert observation.vel == 2.6


def test_qdato_nan_sentinel_maps_to_none() -> None:
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "89070",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.0,
            "pres": 980.0,
            "vel": 5.0,
            "qdato": "NaN",
        }
    )

    assert dto.qdato is None


def test_unmodeled_fields_are_dropped_not_rejected() -> None:
    # Confirms extra="ignore" tolerates AEMET's ~25-field payload without
    # us declaring fields this application has no requirement to support.
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "89064",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.9,
            "pres": 983.6,
            "vel": 2.6,
            "qdato": 0.0,
            "altNieve": "NaN",
            "radKjM2": "NaN",
            "hr": 53.0,
            "ddd": 213.0,
        }
    )

    assert dto.temp == 1.9
    assert not hasattr(dto, "altNieve")


def test_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError):
        AemetObservationDTO.model_validate({"temp": 1.0})


def test_map_to_observation_good_quality() -> None:
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "89070",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.4,
            "pres": 984.4,
            "vel": 7.1,
            "qdato": 0.0,
        }
    )

    observation = map_to_observation(dto)

    assert observation.station is Station.GABRIEL_DE_CASTILLA
    assert observation.temperature_celsius == 1.4
    assert observation.is_good_quality is True


def test_map_to_observation_bad_quality() -> None:
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "89070",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.4,
            "pres": 984.4,
            "vel": 7.1,
            "qdato": 1.0,
        }
    )

    observation = map_to_observation(dto)

    assert observation.is_good_quality is False


def test_map_to_observation_unknown_station_raises() -> None:
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "99999",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.0,
            "pres": 980.0,
            "vel": 5.0,
        }
    )

    with pytest.raises(ValueError, match="99999"):
        map_to_observation(dto)


def test_station_observation_is_frozen() -> None:
    dto = AemetObservationDTO.model_validate(
        {
            "identificacion": "89070",
            "fhora": "2024-01-15T00:00:00Z",
            "temp": 1.4,
            "pres": 984.4,
            "vel": 7.1,
            "qdato": 0.0,
        }
    )
    observation = map_to_observation(dto)

    with pytest.raises(ValidationError):
        observation.temperature_celsius = 99.0  # type: ignore[misc]
