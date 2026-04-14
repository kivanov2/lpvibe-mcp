from unittest.mock import AsyncMock, patch

import pytest

from app.services.github import GitHubService


@pytest.fixture
def gh():
    return GitHubService(token="fake-token", org="test-org")


@pytest.mark.asyncio
async def test_create_repo_success(gh):
    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "html_url": "https://github.com/test-org/my-project",
        "clone_url": "https://github.com/test-org/my-project.git",
    }
    mock_response.raise_for_status = AsyncMock()

    with patch.object(gh._client, "post", return_value=mock_response) as mock_post:
        result = await gh.create_repo("my-project")
        mock_post.assert_called_once()
        assert result["html_url"] == "https://github.com/test-org/my-project"


@pytest.mark.asyncio
async def test_delete_repo_success(gh):
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.raise_for_status = AsyncMock()

    with patch.object(gh._client, "delete", return_value=mock_response):
        await gh.delete_repo("my-project")
