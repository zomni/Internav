"""Add campaigns, fingerprints, access_point_observations tables.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0004"
down_revision = "20260727_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "floor_id",
            sa.String(length=36),
            sa.ForeignKey("floors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Draft"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_campaigns_floor_id", "campaigns", ["floor_id"])

    op.create_table(
        "fingerprints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cell_id",
            sa.String(length=36),
            sa.ForeignKey("cells.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_number", sa.Integer(), nullable=False),
        sa.Column("orientation", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_fingerprints_campaign_id", "fingerprints", ["campaign_id"])
    op.create_index("ix_fingerprints_cell_id", "fingerprints", ["cell_id"])

    op.create_table(
        "access_point_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "fingerprint_id",
            sa.String(length=36),
            sa.ForeignKey("fingerprints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("bssid", sa.String(length=17), nullable=False),
        sa.Column("ssid", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("rssi", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("band", sa.String(length=8), nullable=False, server_default=""),
        sa.Column("security", sa.String(length=32), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_access_point_observations_fingerprint_id",
        "access_point_observations",
        ["fingerprint_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_access_point_observations_fingerprint_id",
        table_name="access_point_observations",
    )
    op.drop_table("access_point_observations")
    op.drop_index("ix_fingerprints_cell_id", table_name="fingerprints")
    op.drop_index("ix_fingerprints_campaign_id", table_name="fingerprints")
    op.drop_table("fingerprints")
    op.drop_index("ix_campaigns_floor_id", table_name="campaigns")
    op.drop_table("campaigns")
