from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-5-5"
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_app_secret: str
    whatsapp_verify_token: str
    whatsapp_api_version: str = "v23.0"
    # JSON in the env var: phone (E.164, no "+") -> user name
    allowed_users: dict[str, str]
    google_client_id: str
    google_client_secret: str
    timezone: str = "America/Sao_Paulo"
    history_limit: int = 20
    history_max_age_hours: int = 24

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
