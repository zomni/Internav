from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.floor_plan import FloorPlan
from app.infrastructure.persistence.models import FloorPlanModel
from app.infrastructure.persistence.repositories.mappers import floor_plan_to_domain


class SqlAlchemyFloorPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: FloorPlan) -> FloorPlan:
        model = FloorPlanModel(
            id=str(entity.id),
            floor_id=str(entity.floor_id),
            image_path=entity.image_path,
            width=entity.width,
            height=entity.height,
            scale=entity.scale,
            checksum=entity.checksum,
            mime_type=entity.mime_type,
            fp_version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return floor_plan_to_domain(model)

    def get(self, entity_id: UUID) -> FloorPlan | None:
        model = self._session.get(FloorPlanModel, str(entity_id))
        return floor_plan_to_domain(model) if model else None

    def list_by_floor(self, floor_id: UUID) -> list[FloorPlan]:
        query = (
            select(FloorPlanModel)
            .where(FloorPlanModel.floor_id == str(floor_id))
            .order_by(FloorPlanModel.fp_version.desc())
        )
        return [floor_plan_to_domain(m) for m in self._session.scalars(query).all()]

    def get_active(self, floor_id: UUID) -> FloorPlan | None:
        model = self._session.scalar(
            select(FloorPlanModel).where(
                FloorPlanModel.floor_id == str(floor_id),
                FloorPlanModel.is_active == True,
                FloorPlanModel.deleted_at.is_(None),
            )
        )
        return floor_plan_to_domain(model) if model else None

    def has_active(self, floor_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(FloorPlanModel.id).where(
                    FloorPlanModel.floor_id == str(floor_id),
                    FloorPlanModel.is_active == True,
                    FloorPlanModel.deleted_at.is_(None),
                )
            )
            is not None
        )

    def deactivate_all(self, floor_id: UUID) -> None:
        from sqlalchemy import update

        self._session.execute(
            update(FloorPlanModel)
            .where(
                FloorPlanModel.floor_id == str(floor_id),
                FloorPlanModel.is_active == True,
            )
            .values(is_active=False)
        )

    def update(self, entity: FloorPlan) -> FloorPlan:
        model = self._session.get(FloorPlanModel, str(entity.id))
        if model is None:
            raise LookupError("FloorPlan not found.")
        model.image_path = entity.image_path
        model.width = entity.width
        model.height = entity.height
        model.scale = entity.scale
        model.checksum = entity.checksum
        model.mime_type = entity.mime_type
        model.fp_version = entity.version
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return floor_plan_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(FloorPlanModel, str(entity_id))
        if model is None:
            raise LookupError("FloorPlan not found.")
        from datetime import UTC, datetime

        model.is_active = False
        model.deleted_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)
        model.updated_by = str(deleted_by) if deleted_by else None
        self._session.flush()
