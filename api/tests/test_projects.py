import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_session

client = TestClient(app, raise_server_exceptions=False)


def _auth_header():
    """Override auth dependency for testing."""
    from app.auth import AuthUser, get_current_user

    user = AuthUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        github_login="testuser",
        github_id=12345,
        jti="test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: user


def _cleanup():
    app.dependency_overrides.clear()


def test_create_project_validates_name():
    _auth_header()
    try:
        resp = client.post("/projects", json={"name": "INVALID NAME!", "template": "fastapi-api"})
        assert resp.status_code == 422
    finally:
        _cleanup()


def test_list_projects_empty():
    _auth_header()
    try:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def mock_get_session():
            yield mock_session

        app.dependency_overrides[get_session] = mock_get_session
        resp = client.get("/projects")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
    finally:
        _cleanup()
