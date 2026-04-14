import re
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Platform DB (SQLAlchemy async)
    database_url: str = "postgresql+asyncpg://platform_admin:changeme@localhost:5432/platform_db"

    # PG admin DSN for raw asyncpg DDL (CREATE DATABASE/ROLE)
    pg_admin_dsn: str = "postgresql://platform_admin:changeme@localhost:5432/postgres"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False

    # GitHub
    gh_admin_token: str = ""
    gh_org: str = "LoyaltyPlant-Vibe"

    # Coolify
    coolify_api_url: str = "https://coolify.alefbet.lphub.net"
    coolify_api_token: str = ""
    coolify_server_uuid: str = "qwswwc4cgkswg4g00w0wsosw"
    coolify_project_uuid: str = "g8ocgc44wg0okscok0ocgwws"
    coolify_environment_name: str = "production"

    # JWT
    jwt_signing_key: str = "changeme-in-production"

    # Platform
    platform_domain: str = "alefbet.lphub.net"


settings = Settings()

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,48}[a-z0-9]$")


def validate_project_name(name: str) -> str:
    if not PROJECT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name '{name}': must be 3-50 chars, "
            "lowercase letters/digits/hyphens, start with letter, end with letter/digit"
        )
    return name
