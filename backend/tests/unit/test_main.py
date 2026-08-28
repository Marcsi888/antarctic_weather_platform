from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_check_returns_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # create_app() builds real Settings() at call time; a fake key and an
    # isolated database path keep this smoke test independent of any real
    # .env file, which does not exist in CI.
    monkeypatch.setenv("AEMET_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()

    from app.main import create_app

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    get_settings.cache_clear()
