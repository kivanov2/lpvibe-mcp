from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]


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
