import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthUser, get_current_user
from app.config import settings, validate_project_name
from app.db import get_session
from app.models import Project, User
from app.schemas import ProjectCreate, ProjectList, ProjectResponse
from app.services.audit import log_action

router = APIRouter(prefix="/projects", tags=["projects"])


async def _ensure_user(session: AsyncSession, auth_user: AuthUser) -> User:
    result = await session.execute(select(User).where(User.github_id == auth_user.github_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=auth_user.user_id,
            github_login=auth_user.github_login,
            github_id=auth_user.github_id,
        )
        session.add(user)
        await session.flush()
    return user


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        validate_project_name(body.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    user = await _ensure_user(session, auth_user)

    existing = await session.execute(
        select(Project).where(Project.user_id == user.id, Project.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Project '{body.name}' already exists")

    from app.main import github_svc, pg_admin_svc, minio_admin_svc, coolify_svc

    project = Project(name=body.name, user_id=user.id, template_id=body.template)
    provisioned = {}

    try:
        if github_svc:
            repo = await github_svc.create_repo(body.name)
            project.github_repo_url = repo["html_url"]
            provisioned["github"] = body.name

        if pg_admin_svc:
            db_info = await pg_admin_svc.create_project_db(body.name)
            project.postgres_db_name = db_info["db_name"]
            project.postgres_user = db_info["db_user"]
            provisioned["postgres"] = db_info

        if minio_admin_svc:
            bucket = minio_admin_svc.create_bucket(body.name)
            project.minio_bucket_name = bucket
            provisioned["minio"] = bucket

        if coolify_svc and project.github_repo_url:
            pg_host = settings.database_url.split("@")[1].split(":")[0]
            env_vars = {
                "DATABASE_URL": (
                    f"postgresql://{db_info['db_user']}:{db_info['db_password']}"
                    f"@{pg_host}:5432/{db_info['db_name']}"
                    if pg_admin_svc and "postgres" in provisioned
                    else ""
                ),
                "S3_ENDPOINT": f"http://{settings.minio_endpoint}",
                "S3_ACCESS_KEY": settings.minio_access_key,
                "S3_SECRET_KEY": settings.minio_secret_key,
                "S3_BUCKET": project.minio_bucket_name or "",
                "PLATFORM_PROJECT_ID": str(project.id),
                "LOG_LEVEL": "info",
            }
            app_data = await coolify_svc.create_app(
                name=body.name,
                repo_url=project.github_repo_url + ".git",
                env_vars=env_vars,
            )
            project.coolify_app_uuid = app_data.get("uuid")
            project.preview_url = app_data.get("fqdn")

        project.state = "created"
        session.add(project)
        await log_action(session, user_id=user.id, action="create_project", project_id=project.id,
                         args={"name": body.name, "template": body.template}, result="success")
        await session.commit()
        await session.refresh(project)
        return project

    except Exception as e:
        await session.rollback()
        await _rollback_provisioned(provisioned, github_svc, pg_admin_svc, minio_admin_svc, coolify_svc)
        raise HTTPException(status_code=500, detail=f"Project creation failed: {e}")


async def _rollback_provisioned(provisioned, github_svc, pg_admin_svc, minio_admin_svc, coolify_svc):
    if "github" in provisioned and github_svc:
        try:
            await github_svc.delete_repo(provisioned["github"])
        except Exception:
            pass
    if "postgres" in provisioned and pg_admin_svc:
        try:
            name = provisioned["postgres"]["db_name"].replace("project_", "").replace("_db", "").replace("_", "-")
            await pg_admin_svc.delete_project_db(name)
        except Exception:
            pass
    if "minio" in provisioned and minio_admin_svc:
        try:
            name = provisioned["minio"].replace("project-", "").replace("-files", "")
            minio_admin_svc.delete_bucket(name)
        except Exception:
            pass


@router.get("", response_model=ProjectList)
async def list_projects(
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Project).where(Project.user_id == auth_user.user_id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return ProjectList(projects=projects, total=len(projects))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == auth_user.user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    auth_user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == auth_user.user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.main import github_svc, pg_admin_svc, minio_admin_svc, coolify_svc

    if project.coolify_app_uuid and coolify_svc:
        try:
            await coolify_svc.delete_app(project.coolify_app_uuid)
        except Exception:
            pass

    if project.github_repo_url and github_svc:
        repo_name = project.github_repo_url.rstrip("/").split("/")[-1]
        try:
            await github_svc.delete_repo(repo_name)
        except Exception:
            pass

    if project.postgres_db_name and pg_admin_svc:
        try:
            await pg_admin_svc.delete_project_db(project.name)
        except Exception:
            pass

    if project.minio_bucket_name and minio_admin_svc:
        try:
            minio_admin_svc.delete_bucket(project.name)
        except Exception:
            pass

    await log_action(session, user_id=auth_user.user_id, action="delete_project",
                     project_id=project.id, result="success")
    await session.delete(project)
    await session.commit()
