"""Settings centralizados (Pydantic). Secretos solo por entorno, jamás en repo."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "turnos-odontologia"
    database_url: str = "postgresql+asyncpg://turnos:turnos@db:5432/turnos"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = "CHANGE-ME"
    jwt_expire_minutes: int = 60
    whatsapp_provider: str = ""
    whatsapp_api_key: str = ""
    mp_access_token: str = ""
    frontend_url: str = "http://localhost:5173"
    appointment_cancel_minutes: int = 120
    late_tolerance_minutes: int = 5
    health_check_timeout_seconds: float = 2.0


settings = Settings()
