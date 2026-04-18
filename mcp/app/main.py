from __future__ import annotations

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.platform_client import PlatformClient

mcp = FastMCP(
    "lpvibe",
    instructions=(
        "Tools for orchestrating LPVibe projects: create/list/get/delete projects. "
        "Each project creates a GitHub repo, Postgres DB, MinIO bucket, and Coolify app."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)

_client = PlatformClient()


@mcp.tool()
async def health_check() -> dict:
    """Return health of the LPVibe Platform API and its dependencies (postgres, redis, minio)."""
    return await _client.health()


@mcp.tool()
async def list_projects() -> dict:
    """List all projects owned by the current user."""
    return await _client.list_projects()


@mcp.tool()
async def create_project(name: str, template: str = "fastapi-api") -> dict:
    """Create a new project. Provisions GitHub repo, Postgres DB, MinIO bucket, Coolify app.

    name: 3-50 chars, lowercase letters/digits/hyphens, start with letter.
    template: e.g. 'fastapi-api', 'nextjs-app'.
    """
    return await _client.create_project(name=name, template=template)


@mcp.tool()
async def get_project(project_id: str) -> dict:
    """Fetch a project's metadata by UUID."""
    return await _client.get_project(project_id)


@mcp.tool()
async def delete_project(project_id: str) -> dict:
    """Delete a project and roll back all provisioned resources (GitHub, PG, MinIO, Coolify)."""
    await _client.delete_project(project_id)
    return {"deleted": project_id}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not settings.mcp_client_token:
            return await call_next(request)
        expected = f"Bearer {settings.mcp_client_token}"
        if request.headers.get("authorization") != expected:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def build_app() -> Starlette:
    inner = mcp.streamable_http_app()
    return Starlette(
        debug=False,
        routes=inner.routes,
        middleware=[Middleware(BearerAuthMiddleware)],
        lifespan=inner.router.lifespan_context,
    )


def run() -> None:
    uvicorn.run(build_app(), host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    run()
