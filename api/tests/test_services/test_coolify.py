from unittest.mock import AsyncMock, patch

import pytest

from app.services.coolify import CoolifyService


@pytest.fixture
def coolify():
    return CoolifyService(
        api_url="https://coolify.test",
        api_token="fake-token",
        server_uuid="srv-123",
        project_uuid="prj-123",
        environment_name="production",
    )


@pytest.mark.asyncio
async def test_create_app(coolify):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"uuid": "app-456", "fqdn": "https://my-svc.test"}
    mock_resp.raise_for_status = AsyncMock()

    with patch.object(coolify._client, "post", return_value=mock_resp):
        result = await coolify.create_app(
            name="my-svc",
            repo_url="https://github.com/org/my-svc.git",
            env_vars={"DATABASE_URL": "postgres://..."},
        )
    assert result["uuid"] == "app-456"


@pytest.mark.asyncio
async def test_delete_app(coolify):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = AsyncMock()

    with patch.object(coolify._client, "delete", return_value=mock_resp):
        await coolify.delete_app("app-456")


@pytest.mark.asyncio
async def test_get_deploy_status(coolify):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "running:healthy"}
    mock_resp.raise_for_status = AsyncMock()

    with patch.object(coolify._client, "get", return_value=mock_resp):
        result = await coolify.get_deploy_status("app-456")
    assert result["status"] == "running:healthy"
