from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import health, projects
from app.services.coolify import CoolifyService
from app.services.github import GitHubService
from app.services.minio_admin import MinIOAdminService
from app.services.postgres_admin import PostgresAdminService

github_svc: GitHubService | None = None
pg_admin_svc: PostgresAdminService | None = None
minio_admin_svc: MinIOAdminService | None = None
coolify_svc: CoolifyService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global github_svc, pg_admin_svc, minio_admin_svc, coolify_svc

    if settings.gh_admin_token:
        github_svc = GitHubService(token=settings.gh_admin_token, org=settings.gh_org)

    if settings.pg_admin_dsn:
        pg_admin_svc = PostgresAdminService(dsn=settings.pg_admin_dsn)

    minio_admin_svc = MinIOAdminService(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )

    if settings.coolify_api_token:
        coolify_svc = CoolifyService(
            api_url=settings.coolify_api_url,
            api_token=settings.coolify_api_token,
            server_uuid=settings.coolify_server_uuid,
            project_uuid=settings.coolify_project_uuid,
            environment_name=settings.coolify_environment_name,
        )

    yield

    if github_svc:
        await github_svc.close()
    if coolify_svc:
        await coolify_svc.close()


app = FastAPI(title="LPVibe Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, tags=["health"])
app.include_router(projects.router)
