"""Add dataset_version column to datasets.

Revision ID: 20260727_0007
Revises: 20260727_0006
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column("dataset_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("datasets", "dataset_version")
