from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aemet_api_key: str = Field(min_length=1)
    aemet_base_url: HttpUrl = HttpUrl("https://opendata.aemet.es/opendata")
    aemet_request_timeout_seconds: float = Field(default=10.0, gt=0)

    database_path: Path = BACKEND_ROOT / "data" / "weather.db"

    log_level: str = "INFO"

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    # pydantic-settings populates required fields from the env at
    # __init__ time; mypy has no plugin for this and sees a missing arg.
    return Settings()  # type: ignore[call-arg]
