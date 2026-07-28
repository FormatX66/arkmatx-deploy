from functools import lru_cache

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

    model_config = SettingsConfigDict(
        env_prefix="ARKMATX_", env_file=".env", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
