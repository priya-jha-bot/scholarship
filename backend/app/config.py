from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg2://scholarship:scholarship@localhost:5432/scholarship"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "scholarship"
    jwt_secret: str = "change-me-long-random"
    jwt_expire_minutes: int = 60
    field_encryption_key: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    frontend_url: str = "http://localhost:5173"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 5
    doc_link_ttl_seconds: int = 600
    rate_limit_enabled: bool = True
    mail_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "no-reply@scholarship.local"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_runtime(self) -> None:
        if not self.field_encryption_key:
            raise RuntimeError(
                "FIELD_ENCRYPTION_KEY is not set. Run `python -m scripts.init_env` or generate one with "
                "python -c \"from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())\""
            )
        if self.env != "dev" and (self.jwt_secret.startswith("change-me") or len(self.jwt_secret) < 32):
            raise RuntimeError("JWT_SECRET must be a random string of at least 32 characters outside dev.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
