from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


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

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalise_db_url(cls, v):
        """Hosts such as Render hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver named."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("postgres://"):
                v = "postgresql+psycopg2://" + v[len("postgres://"):]
            elif v.startswith("postgresql://"):
                v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    def validate_database_url(self) -> None:
        """Fail loudly instead of silently using a local database. Used by the app AND by Alembic (which runs first)."""
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is empty. Set it in the environment (on Render: the Postgres Internal Database URL).")
        try:
            host = make_url(self.database_url).host
        except ArgumentError as e:
            raise RuntimeError("DATABASE_URL is not a valid database URL.") from e
        if self.env != "dev" and host in ("localhost", "127.0.0.1", "::1"):
            raise RuntimeError(
                "DATABASE_URL points to localhost but ENV is not 'dev'. Inside a container localhost is the container itself. "
                "Set DATABASE_URL in the host's environment settings to your managed PostgreSQL Internal Database URL "
                "(and make sure no local .env file was copied into the image)."
            )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_runtime(self) -> None:
        self.validate_database_url()
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
