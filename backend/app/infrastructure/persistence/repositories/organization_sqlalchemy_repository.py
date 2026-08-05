from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.organization import Organization
from app.domain.errors import BusinessRuleViolation
from app.infrastructure.persistence.models import OrganizationModel, SiteModel
from app.infrastructure.persistence.repositories.mappers import organization_to_domain


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Organization) -> Organization:
        model = OrganizationModel(
            id=str(entity.id),
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
        return organization_to_domain(model)

    def get(self, entity_id: UUID) -> Organization | None:
        model = self._session.get(OrganizationModel, str(entity_id))
        return organization_to_domain(model) if model else None

    def get_by_code(self, code: str) -> Organization | None:
        model = self._session.scalar(
            select(OrganizationModel).where(OrganizationModel.code == code)
        )
        return organization_to_domain(model) if model else None

    def list_all(self, is_active: bool | None = True) -> list[Organization]:
        query = select(OrganizationModel)
        if is_active is not None:
            query = query.where(OrganizationModel.is_active == is_active)
        return [organization_to_domain(model) for model in self._session.scalars(query).all()]

    def update(self, entity: Organization) -> Organization:
        model = self._session.get(OrganizationModel, str(entity.id))
        if model is None:
            raise LookupError("Organization not found.")
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
        return organization_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(OrganizationModel, str(entity_id))
        if model is None:
            raise LookupError("Organization not found.")
        has_active_sites = self._session.scalar(
            select(SiteModel.id).where(
                SiteModel.organization_id == str(entity_id),
                SiteModel.deleted_at.is_(None),
            )
        )
        if has_active_sites is not None:
            raise BusinessRuleViolation("Organization cannot be deleted while active Sites exist.")
        entity = organization_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
