from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AuditColumns:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrganizationModel(AuditColumns, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SiteModel(AuditColumns, Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_sites_organization_name"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)


class BuildingModel(AuditColumns, Base):
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_buildings_site_code"),)

    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class FloorModel(AuditColumns, Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "level", name="uq_floors_building_level"),)

    building_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class UserModel(AuditColumns, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )


class FloorPlanModel(AuditColumns, Base):
    __tablename__ = "floor_plans"
    __table_args__ = (
        UniqueConstraint("floor_id", "fp_version", name="uq_floor_plans_floor_version"),
    )

    floor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    scale: Mapped[float] = mapped_column(Float, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    fp_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GridModel(AuditColumns, Base):
    __tablename__ = "grids"

    floor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    cell_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")


class CampaignModel(AuditColumns, Base):
    __tablename__ = "campaigns"

    floor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FingerprintModel(AuditColumns, Base):
    __tablename__ = "fingerprints"

    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cell_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cells.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_number: Mapped[int] = mapped_column(Integer, nullable=False)
    orientation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccessPointObservationModel(AuditColumns, Base):
    __tablename__ = "access_point_observations"

    fingerprint_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fingerprints.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bssid: Mapped[str] = mapped_column(String(17), nullable=False)
    ssid: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    rssi: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    band: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    security: Mapped[str] = mapped_column(String(32), nullable=False, default="")


class DatasetModel(AuditColumns, Base):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")
    fingerprint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    floor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class DatasetCampaignModel(AuditColumns, Base):
    __tablename__ = "dataset_campaigns"
    __table_args__ = (UniqueConstraint("dataset_id", "campaign_id", name="uq_dataset_campaign"),)

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("campaigns.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class ModelVersionModel(AuditColumns, Base):
    __tablename__ = "model_versions"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    floor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("floors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Training")
    hyperparameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CellModel(AuditColumns, Base):
    __tablename__ = "cells"
    __table_args__ = (
        UniqueConstraint("grid_id", "row", "column", name="uq_cells_grid_row_column"),
    )

    grid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grids.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    column: Mapped[int] = mapped_column(Integer, nullable=False)
    center_x: Mapped[float] = mapped_column(Float, nullable=False)
    center_y: Mapped[float] = mapped_column(Float, nullable=False)
    walkable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
