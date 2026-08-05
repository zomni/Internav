from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.site import Site
from app.infrastructure.persistence.models import SiteModel
from app.infrastructure.persistence.repositories.mappers import site_to_domain


class SqlAlchemySiteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Site) -> Site:
        model = SiteModel(
            id=str(entity.id),
            organization_id=str(entity.organization_id),
            name=entity.name,
            code=entity.code,
            timezone=entity.timezone,
            address=entity.address,
            metadata_json=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return site_to_domain(model)

    def get(self, entity_id: UUID) -> Site | None:
        model = self._session.get(SiteModel, str(entity_id))
        return site_to_domain(model) if model else None

    def list_by_organization(self, organization_id: UUID) -> list[Site]:
        models = self._session.scalars(
            select(SiteModel).where(SiteModel.organization_id == str(organization_id))
        ).all()
        return [site_to_domain(model) for model in models]

    def list_all(self, is_active: bool | None = True) -> list[Site]:
        query = select(SiteModel)
        if is_active is not None:
            query = query.where(SiteModel.is_active == is_active)
        return [site_to_domain(model) for model in self._session.scalars(query).all()]

    def update(self, entity: Site) -> Site:
        model = self._session.get(SiteModel, str(entity.id))
        if model is None:
            raise LookupError("Site not found.")
        model.name, model.code, model.timezone = entity.name, entity.code, entity.timezone
        model.address, model.metadata_json = entity.address, entity.metadata
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
        return site_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(SiteModel, str(entity_id))
        if model is None:
            raise LookupError("Site not found.")
        entity = site_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
