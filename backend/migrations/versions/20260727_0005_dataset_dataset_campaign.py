"""Add datasets, dataset_campaigns tables.

Revision ID: 20260727_0005
Revises: 20260727_0004
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0005"
down_revision = "20260727_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Draft"),
        sa.Column("fingerprint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("floor_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "dataset_campaigns",
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
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("dataset_id", "campaign_id", name="uq_dataset_campaign"),
    )
    op.create_index("ix_dataset_campaigns_dataset_id", "dataset_campaigns", ["dataset_id"])
    op.create_index("ix_dataset_campaigns_campaign_id", "dataset_campaigns", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_campaigns_campaign_id", table_name="dataset_campaigns")
    op.drop_index("ix_dataset_campaigns_dataset_id", table_name="dataset_campaigns")
    op.drop_table("dataset_campaigns")
    op.drop_table("datasets")
