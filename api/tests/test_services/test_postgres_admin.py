from unittest.mock import AsyncMock, patch

import pytest

from app.services.postgres_admin import PostgresAdminService


@pytest.fixture
def pg_admin():
    return PostgresAdminService(dsn="postgresql://admin:pass@localhost/postgres")


@pytest.mark.asyncio
async def test_create_project_db(pg_admin):
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("app.services.postgres_admin.asyncpg.connect", return_value=mock_conn):
        result = await pg_admin.create_project_db("my-svc")

    assert result["db_name"] == "project_my_svc_db"
    assert result["db_user"] == "project_my_svc_user"
    assert len(result["db_password"]) > 20
    assert mock_conn.execute.call_count == 3


@pytest.mark.asyncio
async def test_delete_project_db(pg_admin):
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("app.services.postgres_admin.asyncpg.connect", return_value=mock_conn):
        await pg_admin.delete_project_db("my-svc")

    assert mock_conn.execute.call_count == 3
