from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.building import Building
from app.infrastructure.persistence.models import BuildingModel
from app.infrastructure.persistence.repositories.mappers import building_to_domain


class SqlAlchemyBuildingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Building) -> Building:
        model = BuildingModel(
            id=str(entity.id),
            site_id=str(entity.site_id),
            name=entity.name,
            code=entity.code,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return building_to_domain(model)

    def get(self, entity_id: UUID) -> Building | None:
        model = self._session.get(BuildingModel, str(entity_id))
        return building_to_domain(model) if model else None

    def list_by_site(self, site_id: UUID) -> list[Building]:
        models = self._session.scalars(
            select(BuildingModel).where(BuildingModel.site_id == str(site_id))
        ).all()
        return [building_to_domain(model) for model in models]

    def list_all(self, is_active: bool | None = True) -> list[Building]:
        query = select(BuildingModel)
        if is_active is not None:
            query = query.where(BuildingModel.is_active == is_active)
        return [building_to_domain(model) for model in self._session.scalars(query).all()]

    def update(self, entity: Building) -> Building:
        model = self._session.get(BuildingModel, str(entity.id))
        if model is None:
            raise LookupError("Building not found.")
        model.name, model.code, model.description = entity.name, entity.code, entity.description
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
        return building_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(BuildingModel, str(entity_id))
        if model is None:
            raise LookupError("Building not found.")
        entity = building_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
