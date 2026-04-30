import time
import uuid

import httpx
import jwt

from app.config import settings


def _issue_service_jwt() -> str:
    now = int(time.time())
    payload = {
        "user_id": settings.mcp_service_user_id,
        "github_login": settings.mcp_service_github_login,
        "github_id": settings.mcp_service_github_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(payload, settings.jwt_signing_key, algorithm="HS256")


class PlatformClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.platform_api_url, timeout=120.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {_issue_service_jwt()}",
            "Content-Type": "application/json",
        }

    async def health(self) -> dict:
        r = await self._client.get("/health")
        r.raise_for_status()
        return r.json()

    async def create_project(self, name: str, template: str) -> dict:
        r = await self._client.post(
            "/projects",
            json={"name": name, "template": template},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    async def list_projects(self) -> dict:
        r = await self._client.get("/projects", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def get_project(self, project_id: str) -> dict:
        r = await self._client.get(f"/projects/{project_id}", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def delete_project(self, project_id: str) -> None:
        r = await self._client.delete(f"/projects/{project_id}", headers=self._headers())
        r.raise_for_status()

    async def get_project_logs(self, project_id: str, lines: int = 100) -> dict:
        r = await self._client.get(f"/projects/{project_id}/logs", params={"lines": lines}, headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def get_project_status(self, project_id: str) -> dict:
        r = await self._client.get(f"/projects/{project_id}/status", headers=self._headers())
        r.raise_for_status()
        return r.json()

    async def exec_command(self, project_id: str, command: str) -> dict:
        r = await self._client.post(
            f"/projects/{project_id}/exec",
            json={"command": command},
            headers=self._headers(),
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        await self._client.aclose()
