import base64
from unittest.mock import AsyncMock, patch

import pytest

from app.services.coolify import CoolifyService, ExecCommandError


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


def _resp(payload=None):
    resp = AsyncMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status = lambda: None
    return resp


@pytest.mark.asyncio
async def test_exec_command_returns_output(coolify):
    posts = []

    async def post(url, **kwargs):
        posts.append((url, kwargs.get("json")))
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([{"status": "success", "message": "hello", "started_at": "2026-01-01T00:00:00Z"}])

    delete = AsyncMock(return_value=_resp())

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", delete):
        output = await coolify.exec_command("app-456", "echo hello")

    assert output == "hello"
    assert posts[0][0] == "/api/v1/applications/app-456/scheduled-tasks"
    assert posts[0][1]["command"] == "echo hello"
    assert posts[1][0] == "/api/v1/applications/app-456/scheduled-tasks/task-1/execute"
    delete.assert_awaited_once_with("/api/v1/applications/app-456/scheduled-tasks/task-1")


@pytest.mark.asyncio
async def test_exec_command_raises_on_failure(coolify):
    async def post(url, **kwargs):
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([{"status": "failed", "message": "sh: nope: not found", "started_at": "2026-01-01T00:00:00Z"}])

    delete = AsyncMock(return_value=_resp())

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", delete):
        with pytest.raises(ExecCommandError, match="not found"):
            await coolify.exec_command("app-456", "nope")

    delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_exec_command_picks_latest_execution(coolify):
    async def post(url, **kwargs):
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([
            {"status": "failed", "message": "old run", "started_at": "2026-01-01T00:00:00Z"},
            {"status": "success", "message": "new run", "started_at": "2026-01-02T00:00:00Z"},
        ])

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", AsyncMock(return_value=_resp())):
        assert await coolify.exec_command("app-456", "echo new") == "new run"


@pytest.mark.asyncio
async def test_exec_command_times_out_and_cleans_up(coolify):
    async def post(url, **kwargs):
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([])

    delete = AsyncMock(return_value=_resp())

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", delete):
        with pytest.raises(ExecCommandError, match="did not finish"):
            await coolify.exec_command("app-456", "sleep 999", timeout=0)

    delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_exec_command_chunks_long_command(coolify):
    commands = []

    async def post(url, **kwargs):
        payload = kwargs.get("json")
        if payload:
            commands.append(payload["command"])
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([{"status": "success", "message": "done", "started_at": "2026-01-01T00:00:00Z"}])

    long_command = "echo " + "x" * 400

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", AsyncMock(return_value=_resp())):
        assert await coolify.exec_command("app-456", long_command) == "done"

    assert all(len(c) <= 255 for c in commands)
    written = [c for c in commands if c.startswith("printf %s ")]
    assert len(written) > 1
    assert written[0].split()[-2] == ">"
    assert all(c.split()[-2] == ">>" for c in written[1:])

    path = written[0].split()[-1]
    encoded = "".join(c.split()[2] for c in written)
    assert base64.b64decode(encoded).decode() == long_command
    assert f"base64 -d {path} | sh" in commands
    assert f"rm -f {path}" in commands


@pytest.mark.asyncio
async def test_exec_command_cleans_up_after_long_command_fails(coolify):
    commands = []

    async def post(url, **kwargs):
        payload = kwargs.get("json")
        if payload:
            commands.append(payload["command"])
        return _resp({"uuid": "task-1"})

    async def get(url, **kwargs):
        return _resp([{"status": "failed", "message": "boom", "started_at": "2026-01-01T00:00:00Z"}])

    with patch.object(coolify._client, "post", side_effect=post), \
         patch.object(coolify._client, "get", side_effect=get), \
         patch.object(coolify._client, "delete", AsyncMock(return_value=_resp())):
        with pytest.raises(ExecCommandError, match="boom"):
            await coolify.exec_command("app-456", "echo " + "x" * 400)

    assert any(c.startswith("rm -f /tmp/lpvibe-") for c in commands)
