import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_requires_aemet_api_key() -> None:
    with pytest.raises(ValidationError, match="aemet_api_key"):
        Settings(_env_file=None)


def test_settings_loads_valid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEMET_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.aemet_api_key == "test-key"
    assert str(settings.aemet_base_url) == "https://opendata.aemet.es/opendata"
    assert settings.aemet_request_timeout_seconds == 10.0
    assert settings.log_level == "INFO"


def test_settings_rejects_non_positive_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEMET_API_KEY", "test-key")
    monkeypatch.setenv("AEMET_REQUEST_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValidationError, match="aemet_request_timeout_seconds"):
        Settings(_env_file=None)
