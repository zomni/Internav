from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.campaign import Campaign
from app.infrastructure.persistence.models import CampaignModel
from app.infrastructure.persistence.repositories.mappers import campaign_to_domain


class SqlAlchemyCampaignRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Campaign) -> Campaign:
        model = CampaignModel(
            id=str(entity.id),
            floor_id=str(entity.floor_id),
            name=entity.name,
            status=entity.status.value,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return campaign_to_domain(model)

    def get(self, entity_id: UUID) -> Campaign | None:
        model = self._session.get(CampaignModel, str(entity_id))
        return campaign_to_domain(model) if model else None

    def list_all(self) -> list[Campaign]:
        query = (
            select(CampaignModel)
            .where(CampaignModel.deleted_at.is_(None))
            .order_by(CampaignModel.created_at.desc())
        )
        return [campaign_to_domain(m) for m in self._session.scalars(query).all()]

    def list_by_floor(self, floor_id: UUID) -> list[Campaign]:
        query = (
            select(CampaignModel)
            .where(CampaignModel.floor_id == str(floor_id), CampaignModel.deleted_at.is_(None))
            .order_by(CampaignModel.created_at.desc())
        )
        return [campaign_to_domain(m) for m in self._session.scalars(query).all()]

    def has_active_on_floor(self, floor_id: UUID) -> bool:
        from app.domain.entities.campaign import CampaignStatus

        return (
            self._session.scalar(
                select(CampaignModel.id).where(
                    CampaignModel.floor_id == str(floor_id),
                    CampaignModel.status.in_(
                        [CampaignStatus.COLLECTING.value, CampaignStatus.READY.value]
                    ),
                    CampaignModel.deleted_at.is_(None),
                )
            )
            is not None
        )

    def update(self, entity: Campaign) -> Campaign:
        model = self._session.get(CampaignModel, str(entity.id))
        if model is None:
            raise LookupError("Campaign not found.")
        model.floor_id = str(entity.floor_id)
        model.name = entity.name
        model.status = entity.status.value
        model.started_at = entity.started_at
        model.finished_at = entity.finished_at
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return campaign_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(CampaignModel, str(entity_id))
        if model is None:
            raise LookupError("Campaign not found.")
        entity = campaign_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
