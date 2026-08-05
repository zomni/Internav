"""Create core indoor positioning hierarchy.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0001"
down_revision = None
branch_labels = None
depends_on = None


def audit_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        *audit_columns(),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_organizations_code", "organizations", ["code"])

    op.create_table(
        "sites",
        *audit_columns(),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "name", name="uq_sites_organization_name"),
    )
    op.create_index("ix_sites_organization_id", "sites", ["organization_id"])

    op.create_table(
        "buildings",
        *audit_columns(),
        sa.Column("site_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("site_id", "code", name="uq_buildings_site_code"),
    )
    op.create_index("ix_buildings_site_id", "buildings", ["site_id"])

    op.create_table(
        "floors",
        *audit_columns(),
        sa.Column("building_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("building_id", "level", name="uq_floors_building_level"),
    )
    op.create_index("ix_floors_building_id", "floors", ["building_id"])


def downgrade() -> None:
    op.drop_index("ix_floors_building_id", table_name="floors")
    op.drop_table("floors")
    op.drop_index("ix_buildings_site_id", table_name="buildings")
    op.drop_table("buildings")
    op.drop_index("ix_sites_organization_id", table_name="sites")
    op.drop_table("sites")
    op.drop_index("ix_organizations_code", table_name="organizations")
    op.drop_table("organizations")
