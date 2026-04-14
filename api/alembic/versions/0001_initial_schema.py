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
