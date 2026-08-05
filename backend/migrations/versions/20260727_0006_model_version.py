"""Add model_versions table.

Revision ID: 20260727_0006
Revises: 20260727_0005
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0006"
down_revision = "20260727_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "dataset_id",
            sa.String(length=36),
            sa.ForeignKey("datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "floor_id",
            sa.String(length=36),
            sa.ForeignKey("floors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Training"),
        sa.Column("hyperparameters", sa.Text(), nullable=True),
        sa.Column("metrics", sa.Text(), nullable=True),
        sa.Column("training_time", sa.Float(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_versions_dataset_id", "model_versions", ["dataset_id"])
    op.create_index("ix_model_versions_floor_id", "model_versions", ["floor_id"])


def downgrade() -> None:
    op.drop_index("ix_model_versions_floor_id", table_name="model_versions")
    op.drop_index("ix_model_versions_dataset_id", table_name="model_versions")
    op.drop_table("model_versions")
