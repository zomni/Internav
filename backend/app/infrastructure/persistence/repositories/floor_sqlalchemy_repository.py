from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.floor import Floor
from app.infrastructure.persistence.models import FloorModel
from app.infrastructure.persistence.repositories.mappers import floor_to_domain


class SqlAlchemyFloorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Floor) -> Floor:
        model = FloorModel(
            id=str(entity.id),
            building_id=str(entity.building_id),
            name=entity.name,
            level=entity.level,
            display_order=entity.display_order,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return floor_to_domain(model)

    def get(self, entity_id: UUID) -> Floor | None:
        model = self._session.get(FloorModel, str(entity_id))
        return floor_to_domain(model) if model else None

    def list_by_building(self, building_id: UUID) -> list[Floor]:
        models = self._session.scalars(
            select(FloorModel).where(FloorModel.building_id == str(building_id))
        ).all()
        return [floor_to_domain(model) for model in models]

    def list_all(self, is_active: bool | None = True) -> list[Floor]:
        query = select(FloorModel)
        if is_active is not None:
            query = query.where(FloorModel.is_active == is_active)
        return [floor_to_domain(model) for model in self._session.scalars(query).all()]

    def update(self, entity: Floor) -> Floor:
        model = self._session.get(FloorModel, str(entity.id))
        if model is None:
            raise LookupError("Floor not found.")
        model.name, model.level, model.display_order = (
            entity.name,
            entity.level,
            entity.display_order,
        )
        model.updated_at, model.updated_by = (
            entity.updated_at,
            (str(entity.updated_by) if entity.updated_by else None),
        )
        model.version, model.is_active, model.deleted_at = (
            entity.version,
            entity.is_active,
            entity.deleted_at,
        )
        self._session.flush()
        return floor_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(FloorModel, str(entity_id))
        if model is None:
            raise LookupError("Floor not found.")
        entity = floor_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
