"""add coolify_project_uuid to projects

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("coolify_project_uuid", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("projects", "coolify_project_uuid")
