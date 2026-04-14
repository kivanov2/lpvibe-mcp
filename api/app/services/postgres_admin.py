import re
import secrets

import asyncpg

_SAFE_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _sanitize(name: str) -> str:
    ident = name.replace("-", "_")
    if not _SAFE_IDENT.match(ident):
        raise ValueError(f"Unsafe identifier: {ident}")
    return ident


class PostgresAdminService:
    def __init__(self, dsn: str):
        self.dsn = dsn

    async def create_project_db(self, project_name: str) -> dict:
        safe = _sanitize(project_name)
        db_name = f"project_{safe}_db"
        db_user = f"project_{safe}_user"
        db_password = secrets.token_urlsafe(32)

        conn = await asyncpg.connect(self.dsn)
        try:
            await conn.execute(f"CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_password}'")
            await conn.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
            await conn.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
        finally:
            await conn.close()

        return {"db_name": db_name, "db_user": db_user, "db_password": db_password}

    async def delete_project_db(self, project_name: str) -> None:
        safe = _sanitize(project_name)
        db_name = f"project_{safe}_db"
        db_user = f"project_{safe}_user"

        conn = await asyncpg.connect(self.dsn)
        try:
            await conn.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}'"
            )
            await conn.execute(f"DROP DATABASE IF EXISTS {db_name}")
            await conn.execute(f"DROP ROLE IF EXISTS {db_user}")
        finally:
            await conn.close()
