from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities.dataset_campaign import DatasetCampaign
from app.infrastructure.persistence.models import DatasetCampaignModel
from app.infrastructure.persistence.repositories.mappers import dataset_campaign_to_domain


class SqlAlchemyDatasetCampaignRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: DatasetCampaign) -> DatasetCampaign:
        model = DatasetCampaignModel(
            id=str(entity.id),
            dataset_id=str(entity.dataset_id),
            campaign_id=str(entity.campaign_id),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return dataset_campaign_to_domain(model)

    def get(self, entity_id: UUID) -> DatasetCampaign | None:
        model = self._session.get(DatasetCampaignModel, str(entity_id))
        return dataset_campaign_to_domain(model) if model else None

    def list_by_dataset(self, dataset_id: UUID) -> list[DatasetCampaign]:
        query = (
            select(DatasetCampaignModel)
            .where(
                DatasetCampaignModel.dataset_id == str(dataset_id),
                DatasetCampaignModel.deleted_at.is_(None),
            )
            .order_by(DatasetCampaignModel.created_at)
        )
        return [dataset_campaign_to_domain(m) for m in self._session.scalars(query).all()]

    def list_campaign_ids(self, dataset_id: UUID) -> list[UUID]:
        query = (
            select(DatasetCampaignModel.campaign_id)
            .where(
                DatasetCampaignModel.dataset_id == str(dataset_id),
                DatasetCampaignModel.deleted_at.is_(None),
            )
            .order_by(DatasetCampaignModel.created_at)
        )
        return [UUID(row) for row in self._session.scalars(query).all()]

    def delete_by_dataset(self, dataset_id: UUID) -> None:
        self._session.execute(
            delete(DatasetCampaignModel).where(DatasetCampaignModel.dataset_id == str(dataset_id))
        )

    def update(self, entity: DatasetCampaign) -> DatasetCampaign:
        model = self._session.get(DatasetCampaignModel, str(entity.id))
        if model is None:
            raise LookupError("DatasetCampaign not found.")
        model.dataset_id = str(entity.dataset_id)
        model.campaign_id = str(entity.campaign_id)
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return dataset_campaign_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(DatasetCampaignModel, str(entity_id))
        if model is None:
            raise LookupError("DatasetCampaign not found.")
        entity = dataset_campaign_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
