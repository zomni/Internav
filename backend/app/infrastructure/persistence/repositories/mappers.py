from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.access_point_observation import AccessPointObservation
from app.domain.entities.building import Building
from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.entities.cell import Cell
from app.domain.entities.dataset import Dataset, DatasetStatus
from app.domain.entities.dataset_campaign import DatasetCampaign
from app.domain.entities.fingerprint import Fingerprint
from app.domain.entities.floor import Floor
from app.domain.entities.floor_plan import FloorPlan
from app.domain.entities.grid import Grid, GridStatus
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.entities.organization import Organization
from app.domain.entities.site import Site
from app.domain.entities.user import User, UserRole
from app.infrastructure.persistence.models import (
    AccessPointObservationModel,
    BuildingModel,
    CampaignModel,
    CellModel,
    DatasetCampaignModel,
    DatasetModel,
    FingerprintModel,
    FloorModel,
    FloorPlanModel,
    GridModel,
    ModelVersionModel,
    OrganizationModel,
    SiteModel,
    UserModel,
)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def as_optional_utc(value: datetime | None) -> datetime | None:
    return as_utc(value) if value is not None else None


def organization_to_domain(model: OrganizationModel) -> Organization:
    return Organization(
        id=UUID(model.id),
        name=model.name,
        code=model.code,
        description=model.description,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def site_to_domain(model: SiteModel) -> Site:
    return Site(
        id=UUID(model.id),
        organization_id=UUID(model.organization_id),
        name=model.name,
        code=model.code,
        timezone=model.timezone,
        address=model.address,
        metadata=model.metadata_json,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def building_to_domain(model: BuildingModel) -> Building:
    return Building(
        id=UUID(model.id),
        site_id=UUID(model.site_id),
        name=model.name,
        code=model.code,
        description=model.description,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def floor_to_domain(model: FloorModel) -> Floor:
    return Floor(
        id=UUID(model.id),
        building_id=UUID(model.building_id),
        name=model.name,
        level=model.level,
        display_order=model.display_order,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def user_to_domain(model: UserModel) -> User:
    return User(
        id=UUID(model.id),
        email=model.email,
        password_hash=model.password_hash,
        role=UserRole(model.role),
        organization_id=UUID(model.organization_id) if model.organization_id else None,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def floor_plan_to_domain(model: FloorPlanModel) -> FloorPlan:
    return FloorPlan(
        id=UUID(model.id),
        floor_id=UUID(model.floor_id),
        image_path=model.image_path,
        width=model.width,
        height=model.height,
        scale=model.scale,
        checksum=model.checksum,
        mime_type=model.mime_type,
        version=model.fp_version,
        is_active=model.is_active,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
    )


def grid_to_domain(model: GridModel) -> Grid:
    return Grid(
        id=UUID(model.id),
        floor_id=UUID(model.floor_id),
        name=model.name,
        cell_size=model.cell_size,
        status=GridStatus(model.status),
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def cell_to_domain(model: CellModel) -> Cell:
    return Cell(
        id=UUID(model.id),
        grid_id=UUID(model.grid_id),
        row=model.row,
        column=model.column,
        center_x=model.center_x,
        center_y=model.center_y,
        walkable=model.walkable,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def campaign_to_domain(model: CampaignModel) -> Campaign:
    return Campaign(
        id=UUID(model.id),
        floor_id=UUID(model.floor_id),
        name=model.name,
        status=CampaignStatus(model.status),
        started_at=as_optional_utc(model.started_at),
        finished_at=as_optional_utc(model.finished_at),
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def fingerprint_to_domain(model: FingerprintModel) -> Fingerprint:
    return Fingerprint(
        id=UUID(model.id),
        campaign_id=UUID(model.campaign_id),
        cell_id=UUID(model.cell_id),
        device_id=model.device_id,
        captured_at=as_utc(model.captured_at),
        sample_number=model.sample_number,
        orientation=model.orientation,
        notes=model.notes,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def access_point_observation_to_domain(
    model: AccessPointObservationModel,
) -> AccessPointObservation:
    return AccessPointObservation(
        id=UUID(model.id),
        fingerprint_id=UUID(model.fingerprint_id),
        bssid=model.bssid,
        ssid=model.ssid,
        rssi=model.rssi,
        frequency=model.frequency,
        channel=model.channel,
        band=model.band,
        security=model.security,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def dataset_to_domain(model: DatasetModel) -> Dataset:
    return Dataset(
        id=UUID(model.id),
        name=model.name,
        status=DatasetStatus(model.status),
        fingerprint_count=model.fingerprint_count,
        observation_count=model.observation_count,
        floor_count=model.floor_count,
        dataset_version=model.dataset_version,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def dataset_campaign_to_domain(model: DatasetCampaignModel) -> DatasetCampaign:
    return DatasetCampaign(
        id=UUID(model.id),
        dataset_id=UUID(model.dataset_id),
        campaign_id=UUID(model.campaign_id),
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        version=model.version,
        is_active=model.is_active,
    )


def model_version_to_domain(model: ModelVersionModel) -> ModelVersion:
    return ModelVersion(
        id=UUID(model.id),
        dataset_id=UUID(model.dataset_id),
        floor_id=UUID(model.floor_id),
        algorithm=model.algorithm,
        version=model.model_version,
        status=ModelVersionStatus(model.status),
        hyperparameters=model.hyperparameters,
        metrics=model.metrics,
        training_time=model.training_time,
        checksum=model.checksum,
        published_at=as_optional_utc(model.published_at),
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        deleted_at=as_optional_utc(model.deleted_at),
        created_by=UUID(model.created_by) if model.created_by else None,
        updated_by=UUID(model.updated_by) if model.updated_by else None,
        is_active=model.is_active,
    )
