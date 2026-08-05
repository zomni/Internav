"""Add floor_plans, grids, cells tables.

Revision ID: 20260727_0003
Revises: 20260727_0002
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0003"
down_revision = "20260727_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "floor_plans",
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
        sa.Column("image_path", sa.String(length=512), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("scale", sa.Float(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("fp_version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("floor_id", "fp_version", name="uq_floor_plans_floor_version"),
    )
    op.create_index("ix_floor_plans_floor_id", "floor_plans", ["floor_id"])

    op.create_table(
        "grids",
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
        sa.Column("cell_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Draft"),
    )
    op.create_index("ix_grids_floor_id", "grids", ["floor_id"])

    op.create_table(
        "cells",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "grid_id",
            sa.String(length=36),
            sa.ForeignKey("grids.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("column", sa.Integer(), nullable=False),
        sa.Column("center_x", sa.Float(), nullable=False),
        sa.Column("center_y", sa.Float(), nullable=False),
        sa.Column("walkable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("grid_id", "row", "column", name="uq_cells_grid_row_column"),
    )
    op.create_index("ix_cells_grid_id", "cells", ["grid_id"])


def downgrade() -> None:
    op.drop_index("ix_cells_grid_id", table_name="cells")
    op.drop_table("cells")
    op.drop_index("ix_grids_floor_id", table_name="grids")
    op.drop_table("grids")
    op.drop_index("ix_floor_plans_floor_id", table_name="floor_plans")
    op.drop_table("floor_plans")
