# Platform API (Plan B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Platform API — a FastAPI service orchestrating project lifecycle (CRUD) across GitHub, PostgreSQL, MinIO, and Coolify, with JWT auth and audit logging.

**Architecture:** Async FastAPI on port 8000. SQLAlchemy 2.0 async ORM for platform metadata (users, projects, audit_log). httpx async clients for GitHub/Coolify REST APIs. MinIO Python SDK for storage. Redis for anti-loop counters and locks. All infra services are already running in Coolify on the `coolify` Docker network — the API container joins this network automatically when deployed via Coolify.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, httpx, minio, redis, PyJWT, pydantic-settings, pytest + pytest-asyncio

**Prerequisites:**
- Coolify project "LPVibe Platform" (UUID: `g8ocgc44wg0okscok0ocgwws`)
- PostgreSQL (UUID: `kwoosws88wgkk4scwo0ccccg`) — running:healthy
- Redis (UUID: `zss0gsg0g4c480g444cgw4sg`) — running:healthy
- MinIO service (UUID: `osowcgcso44sw08skoswcg4c`) — running:healthy
- Server (UUID: `qwswwc4cgkswg4g00w0wsosw`)

---

## File Structure

```
api/
├── pyproject.toml
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, router includes
│   ├── config.py                  # pydantic-settings, all env vars
│   ├── db.py                      # async engine, session factory
│   ├── models.py                  # User, Project, AuditLog ORM models
│   ├── schemas.py                 # Pydantic request/response models
│   ├── auth.py                    # JWT validation FastAPI dependency
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py              # GET /health
│   │   └── projects.py            # POST/GET/DELETE /projects
│   └── services/
│       ├── __init__.py
│       ├── github.py              # Create/delete repos, push templates
│       ├── coolify.py             # Create/delete apps, inject env, status
│       ├── postgres_admin.py      # Create/delete per-project DBs and roles
│       ├── minio_admin.py         # Create/delete buckets
│       └── audit.py               # Log actions to audit_log table
└── tests/
    ├── __init__.py
    ├── conftest.py                # test fixtures, mock DB, TestClient
    ├── test_health.py
    ├── test_auth.py
    ├── test_projects.py
    └── test_services/
        ├── __init__.py
        ├── test_github.py
        ├── test_coolify.py
        ├── test_postgres_admin.py
        └── test_minio_admin.py
```

---

## Task 1: Project Scaffolding + Config

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/app/__init__.py`
- Create: `api/app/config.py`
- Create: `api/app/routers/__init__.py`
- Create: `api/app/services/__init__.py`
- Create: `api/tests/__init__.py`
- Create: `api/tests/test_services/__init__.py`

- [ ] **Step 1: Create `api/pyproject.toml`**

```toml
[project]
name = "lpvibe-platform-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "httpx>=0.28",
    "minio>=7.2",
    "redis>=5.2",
    "PyJWT[crypto]>=2.10",
    "pydantic-settings>=2.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "httpx",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `api/app/config.py`**

```python
import re
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Platform DB (SQLAlchemy async)
    database_url: str = "postgresql+asyncpg://platform_admin:changeme@localhost:5432/platform_db"

    # PG admin DSN for raw asyncpg DDL (CREATE DATABASE/ROLE)
    # Points to 'postgres' db, not 'platform_db'
    pg_admin_dsn: str = "postgresql://platform_admin:changeme@localhost:5432/postgres"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False

    # GitHub
    gh_admin_token: str = ""
    gh_org: str = "LoyaltyPlant-Vibe"

    # Coolify
    coolify_api_url: str = "https://coolify.alefbet.lphub.net"
    coolify_api_token: str = ""
    coolify_server_uuid: str = "qwswwc4cgkswg4g00w0wsosw"
    coolify_project_uuid: str = "g8ocgc44wg0okscok0ocgwws"
    coolify_environment_name: str = "production"

    # JWT
    jwt_signing_key: str = "changeme-in-production"

    # Platform
    platform_domain: str = "alefbet.lphub.net"


settings = Settings()


# Project name validation: lowercase letters, digits, hyphens only
PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,48}[a-z0-9]$")


def validate_project_name(name: str) -> str:
    if not PROJECT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name '{name}': must be 3-50 chars, "
            "lowercase letters/digits/hyphens, start with letter, end with letter/digit"
        )
    return name
```

- [ ] **Step 3: Create empty `__init__.py` files**

Create these empty files:
- `api/app/__init__.py`
- `api/app/routers/__init__.py`
- `api/app/services/__init__.py`
- `api/tests/__init__.py`
- `api/tests/test_services/__init__.py`

- [ ] **Step 4: Install dependencies**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
pip install -e ".[dev]"
```

- [ ] **Step 5: Verify config loads**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
python -c "from app.config import settings; print(settings.platform_domain)"
```

Expected: `alefbet.lphub.net`

- [ ] **Step 6: Commit**

```bash
git add api/
git commit -m "chore: scaffold Platform API with config and dependencies"
```

---

## Task 2: Database Models + Migration

**Files:**
- Create: `api/app/db.py`
- Create: `api/app/models.py`
- Create: `api/alembic.ini`
- Create: `api/alembic/env.py`
- Create: `api/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Create `api/app/db.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create `api/app/models.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    github_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    github_repo_url: Mapped[str | None] = mapped_column(String(500))
    postgres_db_name: Mapped[str | None] = mapped_column(String(100))
    postgres_user: Mapped[str | None] = mapped_column(String(100))
    minio_bucket_name: Mapped[str | None] = mapped_column(String(100))
    coolify_app_uuid: Mapped[str | None] = mapped_column(String(100))
    preview_url: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(50), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    args: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Create `api/alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://platform_admin:changeme@localhost:5432/platform_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 4: Create `api/alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 5: Create initial migration `api/alembic/versions/0001_initial_schema.py`**

```python
"""initial schema: users, projects, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("github_login", sa.String(255), unique=True, nullable=False),
        sa.Column("github_id", sa.Integer, unique=True, nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("github_repo_url", sa.String(500)),
        sa.Column("postgres_db_name", sa.String(100)),
        sa.Column("postgres_user", sa.String(100)),
        sa.Column("minio_bucket_name", sa.String(100)),
        sa.Column("coolify_app_uuid", sa.String(100)),
        sa.Column("preview_url", sa.String(500)),
        sa.Column("state", sa.String(50), server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("args", JSONB),
        sa.Column("result", sa.String(50)),
        sa.Column("error_message", sa.Text),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("audit_log")
    op.drop_table("projects")
    op.drop_table("users")
```

- [ ] **Step 6: Verify models import cleanly**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
python -c "from app.models import User, Project, AuditLog; print('Models OK')"
```

Expected: `Models OK`

- [ ] **Step 7: Commit**

```bash
git add api/app/db.py api/app/models.py api/alembic.ini api/alembic/
git commit -m "feat(api): add database models and initial Alembic migration"
```

---

## Task 3: FastAPI App + Health Endpoint

**Files:**
- Create: `api/app/main.py`
- Create: `api/app/routers/health.py`
- Create: `api/app/schemas.py` (start with health schemas)
- Create: `api/tests/conftest.py`
- Create: `api/tests/test_health.py`

- [ ] **Step 1: Write `api/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_includes_services():
    response = client.get("/health")
    data = response.json()
    assert "services" in data
    for svc in ("postgres", "redis", "minio"):
        assert svc in data["services"]
```

- [ ] **Step 2: Create `api/app/schemas.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]


# --- Projects ---

class ProjectCreate(BaseModel):
    name: str
    template: str


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID
    template_id: str
    github_repo_url: str | None
    postgres_db_name: str | None
    minio_bucket_name: str | None
    coolify_app_uuid: str | None
    preview_url: str | None
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectList(BaseModel):
    projects: list[ProjectResponse]
    total: int
```

- [ ] **Step 3: Create `api/app/routers/health.py`**

```python
from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    # MVP: report ok without actually pinging services
    # Real checks added after deployment when services are reachable
    return HealthResponse(
        status="ok",
        services={
            "postgres": "ok",
            "redis": "ok",
            "minio": "ok",
        },
    )
```

- [ ] **Step 4: Create `api/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: could run migrations, warm up connections
    yield
    # Shutdown: close pools


app = FastAPI(title="LPVibe Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, tags=["health"])
```

- [ ] **Step 5: Create `api/tests/conftest.py`**

```python
# Shared fixtures for tests. Currently empty — will add DB session mocks later.
```

- [ ] **Step 6: Run tests**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
python -m pytest tests/test_health.py -v
```

Expected: 2 passed

- [ ] **Step 7: Verify uvicorn starts**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
timeout 3 uvicorn app.main:app --host 0.0.0.0 --port 8000 || true
```

Expected: server starts (exits on timeout, that's fine)

- [ ] **Step 8: Commit**

```bash
git add api/app/main.py api/app/schemas.py api/app/routers/health.py api/tests/
git commit -m "feat(api): add FastAPI app with health endpoint"
```

---

## Task 4: GitHub Integration Service

**Files:**
- Create: `api/app/services/github.py`
- Create: `api/tests/test_services/test_github.py`

- [ ] **Step 1: Write `api/tests/test_services/test_github.py`**

```python
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
        await gh.delete_repo("my-project")  # should not raise
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
python -m pytest tests/test_services/test_github.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Create `api/app/services/github.py`**

```python
import httpx


class GitHubService:
    def __init__(self, token: str, org: str):
        self.org = org
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )

    async def create_repo(self, name: str, private: bool = True) -> dict:
        resp = await self._client.post(
            f"/orgs/{self.org}/repos",
            json={"name": name, "private": private, "auto_init": True},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"html_url": data["html_url"], "clone_url": data["clone_url"]}

    async def delete_repo(self, name: str) -> None:
        resp = await self._client.delete(f"/repos/{self.org}/{name}")
        resp.raise_for_status()

    async def close(self):
        await self._client.aclose()
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_services/test_github.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add api/app/services/github.py api/tests/test_services/test_github.py
git commit -m "feat(api): add GitHub integration service (create/delete repo)"
```

---

## Task 5: PostgreSQL Admin Service

**Files:**
- Create: `api/app/services/postgres_admin.py`
- Create: `api/tests/test_services/test_postgres_admin.py`

- [ ] **Step 1: Write `api/tests/test_services/test_postgres_admin.py`**

```python
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
    assert mock_conn.execute.call_count == 3  # CREATE ROLE, CREATE DB, GRANT


@pytest.mark.asyncio
async def test_delete_project_db(pg_admin):
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("app.services.postgres_admin.asyncpg.connect", return_value=mock_conn):
        await pg_admin.delete_project_db("my-svc")

    assert mock_conn.execute.call_count == 2  # DROP DB, DROP ROLE
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_services/test_postgres_admin.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `api/app/services/postgres_admin.py`**

```python
import re
import secrets

import asyncpg

_SAFE_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _sanitize(name: str) -> str:
    """Convert project name to safe SQL identifier (hyphens → underscores)."""
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
            # Terminate connections to the DB before dropping
            await conn.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}'"
            )
            await conn.execute(f"DROP DATABASE IF EXISTS {db_name}")
            await conn.execute(f"DROP ROLE IF EXISTS {db_user}")
        finally:
            await conn.close()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_services/test_postgres_admin.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add api/app/services/postgres_admin.py api/tests/test_services/test_postgres_admin.py
git commit -m "feat(api): add PostgreSQL admin service (per-project DB provisioning)"
```

---

## Task 6: MinIO Integration Service

**Files:**
- Create: `api/app/services/minio_admin.py`
- Create: `api/tests/test_services/test_minio_admin.py`

- [ ] **Step 1: Write `api/tests/test_services/test_minio_admin.py`**

```python
from unittest.mock import MagicMock, patch

import pytest

from app.services.minio_admin import MinIOAdminService


@pytest.fixture
def minio_svc():
    return MinIOAdminService(endpoint="localhost:9000", access_key="admin", secret_key="pass", secure=False)


def test_create_bucket(minio_svc):
    with patch.object(minio_svc._client, "bucket_exists", return_value=False), \
         patch.object(minio_svc._client, "make_bucket") as mock_make:
        result = minio_svc.create_bucket("my-svc")
        assert result == "project-my-svc-files"
        mock_make.assert_called_once_with("project-my-svc-files")


def test_create_bucket_already_exists(minio_svc):
    with patch.object(minio_svc._client, "bucket_exists", return_value=True), \
         patch.object(minio_svc._client, "make_bucket") as mock_make:
        result = minio_svc.create_bucket("my-svc")
        assert result == "project-my-svc-files"
        mock_make.assert_not_called()


def test_delete_bucket(minio_svc):
    with patch.object(minio_svc._client, "bucket_exists", return_value=True), \
         patch.object(minio_svc._client, "list_objects", return_value=[]), \
         patch.object(minio_svc._client, "remove_bucket") as mock_rm:
        minio_svc.delete_bucket("my-svc")
        mock_rm.assert_called_once_with("project-my-svc-files")
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_services/test_minio_admin.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `api/app/services/minio_admin.py`**

```python
from minio import Minio


class MinIOAdminService:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def _bucket_name(self, project_name: str) -> str:
        return f"project-{project_name}-files"

    def create_bucket(self, project_name: str) -> str:
        bucket = self._bucket_name(project_name)
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)
        return bucket

    def delete_bucket(self, project_name: str) -> None:
        bucket = self._bucket_name(project_name)
        if not self._client.bucket_exists(bucket):
            return
        # Remove all objects first
        objects = self._client.list_objects(bucket, recursive=True)
        for obj in objects:
            self._client.remove_object(bucket, obj.object_name)
        self._client.remove_bucket(bucket)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_services/test_minio_admin.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add api/app/services/minio_admin.py api/tests/test_services/test_minio_admin.py
git commit -m "feat(api): add MinIO admin service (per-project bucket management)"
```

---

## Task 7: Coolify Integration Service

**Files:**
- Create: `api/app/services/coolify.py`
- Create: `api/tests/test_services/test_coolify.py`

- [ ] **Step 1: Write `api/tests/test_services/test_coolify.py`**

```python
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
        await coolify.delete_app("app-456")  # should not raise


@pytest.mark.asyncio
async def test_get_deploy_status(coolify):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "running:healthy"}
    mock_resp.raise_for_status = AsyncMock()

    with patch.object(coolify._client, "get", return_value=mock_resp):
        result = await coolify.get_deploy_status("app-456")
    assert result["status"] == "running:healthy"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_services/test_coolify.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `api/app/services/coolify.py`**

```python
import httpx


class CoolifyService:
    def __init__(
        self,
        api_url: str,
        api_token: str,
        server_uuid: str,
        project_uuid: str,
        environment_name: str,
    ):
        self.server_uuid = server_uuid
        self.project_uuid = project_uuid
        self.environment_name = environment_name
        self._client = httpx.AsyncClient(
            base_url=api_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def create_app(self, name: str, repo_url: str, env_vars: dict[str, str]) -> dict:
        resp = await self._client.post(
            "/api/v1/applications",
            json={
                "name": name,
                "server_uuid": self.server_uuid,
                "project_uuid": self.project_uuid,
                "environment_name": self.environment_name,
                "git_repository": repo_url,
                "git_branch": "main",
                "build_pack": "dockerfile",
                "instant_deploy": False,
            },
        )
        resp.raise_for_status()
        app_data = resp.json()
        app_uuid = app_data["uuid"]

        # Inject environment variables
        for key, value in env_vars.items():
            await self._client.post(
                f"/api/v1/applications/{app_uuid}/envs",
                json={"key": key, "value": value},
            )

        return app_data

    async def deploy_app(self, app_uuid: str) -> dict:
        resp = await self._client.post(f"/api/v1/deploy", json={"tag_or_uuid": app_uuid, "force": True})
        resp.raise_for_status()
        return resp.json()

    async def get_deploy_status(self, app_uuid: str) -> dict:
        resp = await self._client.get(f"/api/v1/applications/{app_uuid}")
        resp.raise_for_status()
        return resp.json()

    async def delete_app(self, app_uuid: str) -> None:
        resp = await self._client.delete(
            f"/api/v1/applications/{app_uuid}",
            params={"delete_volumes": True},
        )
        resp.raise_for_status()

    async def close(self):
        await self._client.aclose()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_services/test_coolify.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add api/app/services/coolify.py api/tests/test_services/test_coolify.py
git commit -m "feat(api): add Coolify integration service (app lifecycle + deploy)"
```

---

## Task 8: Audit Logging Service

**Files:**
- Create: `api/app/services/audit.py`

- [ ] **Step 1: Create `api/app/services/audit.py`**

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    project_id: uuid.UUID | None = None,
    args: dict | None = None,
    result: str = "success",
    error_message: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        project_id=project_id,
        args=args,
        result=result,
        error_message=error_message,
    )
    session.add(entry)
    # Flush but don't commit — let the calling endpoint manage the transaction
    await session.flush()
```

- [ ] **Step 2: Commit**

```bash
git add api/app/services/audit.py
git commit -m "feat(api): add audit logging service"
```

---

## Task 9: Auth Middleware (JWT Validation)

**Files:**
- Create: `api/app/auth.py`
- Create: `api/tests/test_auth.py`

- [ ] **Step 1: Write `api/tests/test_auth.py`**

```python
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth import get_current_user, AuthUser
from app.config import settings

app = FastAPI()


@app.get("/protected")
async def protected(user: AuthUser = Depends(get_current_user)):
    return {"user_id": str(user.user_id), "github_login": user.github_login}


client = TestClient(app, raise_server_exceptions=False)


def _make_token(payload_overrides: dict | None = None, key: str | None = None) -> str:
    payload = {
        "user_id": str(uuid.uuid4()),
        "github_login": "testuser",
        "github_id": 12345,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, key or settings.jwt_signing_key, algorithm="HS256")


def test_valid_token():
    token = _make_token()
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["github_login"] == "testuser"


def test_missing_token():
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_expired_token():
    token = _make_token({"exp": datetime.now(timezone.utc) - timedelta(hours=1)})
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_invalid_signature():
    token = _make_token(key="wrong-key")
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `api/app/auth.py`**

```python
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    user_id: uuid.UUID
    github_login: str
    github_id: int
    jti: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_signing_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return AuthUser(
        user_id=uuid.UUID(payload["user_id"]),
        github_login=payload["github_login"],
        github_id=payload["github_id"],
        jti=payload.get("jti", ""),
    )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_auth.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add api/app/auth.py api/tests/test_auth.py
git commit -m "feat(api): add JWT auth middleware"
```

---

## Task 10: Project CRUD Endpoints

**Files:**
- Create: `api/app/routers/projects.py`
- Create: `api/tests/test_projects.py`
- Modify: `api/app/main.py` — add projects router
- Modify: `api/app/main.py` — add service initialization in lifespan

This is the core task. The `POST /projects` endpoint orchestrates GitHub → PG → MinIO → Coolify → DB insert. `GET` reads from DB. `DELETE` tears down all resources.

- [ ] **Step 1: Write `api/tests/test_projects.py`**

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _auth_header(user_id: str | None = None):
    """Create a valid auth header by mocking the dependency."""
    from app.auth import AuthUser, get_current_user

    user = AuthUser(
        user_id=uuid.UUID(user_id or "00000000-0000-0000-0000-000000000001"),
        github_login="testuser",
        github_id=12345,
        jti="test-jti",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return {}  # no actual header needed when dependency is overridden


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


def test_create_project_validates_name():
    _auth_header()
    resp = client.post("/projects", json={"name": "INVALID NAME!", "template": "fastapi-api"})
    assert resp.status_code == 422


def test_list_projects_empty():
    _auth_header()
    with patch("app.routers.projects.get_session") as mock_gs:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_gs.return_value = mock_session
        resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_projects.py -v
```

Expected: FAIL

- [ ] **Step 3: Create `api/app/routers/projects.py`**

```python
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
    """Get or create user record from JWT claims."""
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

    # Check name uniqueness for this user
    existing = await session.execute(
        select(Project).where(Project.user_id == user.id, Project.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Project '{body.name}' already exists")

    # Import services lazily to allow testing with mocks
    from app.main import github_svc, pg_admin_svc, minio_admin_svc, coolify_svc

    project = Project(name=body.name, user_id=user.id, template_id=body.template)
    provisioned = {}

    try:
        # 1. GitHub repo
        if github_svc:
            repo = await github_svc.create_repo(body.name)
            project.github_repo_url = repo["html_url"]
            provisioned["github"] = body.name

        # 2. PostgreSQL per-project DB
        if pg_admin_svc:
            db_info = await pg_admin_svc.create_project_db(body.name)
            project.postgres_db_name = db_info["db_name"]
            project.postgres_user = db_info["db_user"]
            provisioned["postgres"] = db_info

        # 3. MinIO bucket
        if minio_admin_svc:
            bucket = minio_admin_svc.create_bucket(body.name)
            project.minio_bucket_name = bucket
            provisioned["minio"] = bucket

        # 4. Coolify app
        if coolify_svc and project.github_repo_url:
            pg_host = settings.database_url.split("@")[1].split(":")[0]  # extract PG host
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
        # Best-effort rollback of provisioned resources
        await _rollback_provisioned(provisioned, github_svc, pg_admin_svc, minio_admin_svc, coolify_svc)
        raise HTTPException(status_code=500, detail=f"Project creation failed: {e}")


async def _rollback_provisioned(provisioned, github_svc, pg_admin_svc, minio_admin_svc, coolify_svc):
    """Best-effort cleanup of partially provisioned resources."""
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

    # Teardown external resources (best-effort)
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
```

- [ ] **Step 4: Update `api/app/main.py` — add projects router + service init**

Replace the entire `api/app/main.py` with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import health, projects
from app.services.coolify import CoolifyService
from app.services.github import GitHubService
from app.services.minio_admin import MinIOAdminService
from app.services.postgres_admin import PostgresAdminService

# Module-level service instances — initialized in lifespan, None during tests
github_svc: GitHubService | None = None
pg_admin_svc: PostgresAdminService | None = None
minio_admin_svc: MinIOAdminService | None = None
coolify_svc: CoolifyService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global github_svc, pg_admin_svc, minio_admin_svc, coolify_svc

    # Initialize services (skip if credentials not configured)
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

    # Cleanup
    if github_svc:
        await github_svc.close()
    if coolify_svc:
        await coolify_svc.close()


app = FastAPI(title="LPVibe Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, tags=["health"])
app.include_router(projects.router)
```

- [ ] **Step 5: Run all tests**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
python -m pytest tests/ -v
```

Expected: all tests pass (health: 2, auth: 4, github: 2, pg_admin: 2, minio: 3, coolify: 3, projects: 2 = 18 total)

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/projects.py api/app/main.py api/tests/test_projects.py
git commit -m "feat(api): add project CRUD endpoints with full orchestration"
```

---

## Task 11: Dockerfile + Local Verification

**Files:**
- Create: `api/Dockerfile`

- [ ] **Step 1: Create `api/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 2: Build Docker image locally**

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp/api
docker build -t lpvibe-platform-api:latest .
```

Expected: build succeeds

- [ ] **Step 3: Run all tests one final time**

```bash
python -m pytest tests/ -v
```

Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add api/Dockerfile
git commit -m "feat(api): add Dockerfile with Alembic migration on startup"
```

---

## Task 12: Deploy Platform API to Coolify

**Files:** none (Coolify MCP operations only)

This task deploys the Platform API to the VPS via Coolify. First we push code to GitHub, then create a Coolify application.

- [ ] **Step 1: Create GitHub repository**

Create a GitHub repo for the platform code. Use the `gh` CLI or GitHub API.

```bash
cd /Users/k.ivanov/projects/vibecoding/lpvibe-mcp
gh repo create LoyaltyPlant-Vibe/lpvibe-mcp --private --source=. --remote=origin --push
```

If the org doesn't work, use personal account:
```bash
gh repo create kivanov2/lpvibe-mcp --private --source=. --remote=origin --push
```

- [ ] **Step 2: Create Coolify application via MCP**

Use `mcp__coolify__application` (or the available Coolify MCP tool) to create an application:
- Name: `lpvibe-platform-api`
- Git repo: the repo URL from step 1
- Branch: `master`
- Build pack: `dockerfile`
- Dockerfile path: `api/Dockerfile`
- Project UUID: `g8ocgc44wg0okscok0ocgwws`
- Server UUID: `qwswwc4cgkswg4g00w0wsosw`
- Environment: `production`

- [ ] **Step 3: Configure environment variables**

Set these env vars on the Coolify application (via `mcp__coolify__env_vars` or `mcp__coolify__bulk_env_update`):

```
DATABASE_URL=postgresql+asyncpg://platform_admin:<PG_PASSWORD>@kwoosws88wgkk4scwo0ccccg:5432/platform_db
PG_ADMIN_DSN=postgresql://platform_admin:<PG_PASSWORD>@kwoosws88wgkk4scwo0ccccg:5432/postgres
REDIS_URL=redis://default:<REDIS_PASSWORD>@zss0gsg0g4c480g444cgw4sg:6379/0
MINIO_ENDPOINT=minio-osowcgcso44sw08skoswcg4c:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=<MINIO_PASSWORD>
COOLIFY_API_URL=https://coolify.alefbet.lphub.net
COOLIFY_API_TOKEN=<COOLIFY_TOKEN>
COOLIFY_SERVER_UUID=qwswwc4cgkswg4g00w0wsosw
COOLIFY_PROJECT_UUID=g8ocgc44wg0okscok0ocgwws
JWT_SIGNING_KEY=<GENERATE_SECURE_KEY>
PLATFORM_DOMAIN=alefbet.lphub.net
```

Note: replace `<PG_PASSWORD>`, `<REDIS_PASSWORD>`, `<MINIO_PASSWORD>` with actual passwords from Coolify database/service configs. `<COOLIFY_TOKEN>` comes from Coolify Settings > API. `<GENERATE_SECURE_KEY>` — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

- [ ] **Step 4: Deploy**

Trigger deployment via Coolify MCP:
```
mcp__coolify__deploy(tag_or_uuid=<app_uuid>)
```

- [ ] **Step 5: Verify health endpoint**

Once deployed, check:
```
curl https://lpvibe-api.alefbet.lphub.net/health
```

Expected:
```json
{"status": "ok", "services": {"postgres": "ok", "redis": "ok", "minio": "ok"}}
```

- [ ] **Step 6: Run Alembic migration verification**

The Dockerfile CMD runs `alembic upgrade head` before starting uvicorn. Check the application logs to verify migration ran successfully.

- [ ] **Step 7: Final commit tag**

```bash
git tag plan-b-complete
git push --tags
```

---

## Plan B Complete — Deliverables Checklist

After completing all tasks:

- [ ] FastAPI app starts and serves `/health`
- [ ] Database schema (users, projects, audit_log) migrated via Alembic
- [ ] JWT auth middleware validates tokens
- [ ] `POST /projects` creates GitHub repo + PG DB + MinIO bucket + Coolify app
- [ ] `GET /projects` lists user's projects
- [ ] `GET /projects/{id}` returns project details
- [ ] `DELETE /projects/{id}` tears down all resources
- [ ] Audit log records all actions
- [ ] All unit tests pass
- [ ] Deployed to Coolify and accessible via HTTPS
- [ ] Alembic migration runs on container startup

**Deferred to later plans:**
- `POST /runtime/run` — sandboxed command execution
- `GET /logs` — OpenSearch integration
- `POST /redeploy` — Coolify redeploy trigger
- Fluent Bit log shipping
- Playwright E2E integration

**Next:** Plan C (MCP Server) — implements the MCP tool surface that Claude Code connects to, calling this Platform API.
