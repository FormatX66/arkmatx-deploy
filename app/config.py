from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Arkmatx Deploy"
    environment: str = "development"
    database_path: str = "data/arkmatx.sqlite3"
    master_key: str = ""
    boxbrain_url: str = ""
    boxbrain_token: str = ""
    allow_network_probes: bool = False
    allow_private_targets: bool = False
    allow_untrusted_tls: bool = False
    connection_timeout_seconds: float = Field(default=6.0, ge=1.0, le=12.0)
    connection_test_rate_limit: int = Field(default=5, ge=1, le=30)
    connection_test_rate_window_seconds: int = Field(default=60, ge=10, le=600)

    model_config = SettingsConfigDict(
        env_prefix="ARKMATX_", env_file=".env", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
