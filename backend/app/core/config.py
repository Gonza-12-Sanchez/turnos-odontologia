"""Settings centralizados (Pydantic). Secretos solo por entorno, jamás en repo."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "turnos-odontologia"
    database_url: str = "postgresql+asyncpg://turnos:turnos@db:5432/turnos"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = "CHANGE-ME"
    jwt_expire_minutes: int = 60
    refresh_expire_days: int = 7
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    bcrypt_rounds: int = 12
    frontend_url: str = "http://localhost:5173"
    whatsapp_provider: str = ""
    whatsapp_api_key: str = ""
    mp_access_token: str = ""
    appointment_cancel_minutes: int = 120
    late_tolerance_minutes: int = 5
    health_check_timeout_seconds: float = 2.0

    @field_validator("cookie_samesite")
    @classmethod
    def _validate_samesite(cls, v: str) -> str:
        if v.lower() not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE debe ser lax, strict o none")
        return v.lower()


settings = Settings()
