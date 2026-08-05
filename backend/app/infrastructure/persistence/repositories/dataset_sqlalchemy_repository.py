from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.dataset import Dataset
from app.infrastructure.persistence.models import DatasetModel
from app.infrastructure.persistence.repositories.mappers import dataset_to_domain


class SqlAlchemyDatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Dataset) -> Dataset:
        model = DatasetModel(
            id=str(entity.id),
            name=entity.name,
            status=entity.status.value,
            fingerprint_count=entity.fingerprint_count,
            observation_count=entity.observation_count,
            floor_count=entity.floor_count,
            dataset_version=entity.dataset_version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return dataset_to_domain(model)

    def get(self, entity_id: UUID) -> Dataset | None:
        model = self._session.get(DatasetModel, str(entity_id))
        return dataset_to_domain(model) if model else None

    def list_all(self) -> list[Dataset]:
        query = (
            select(DatasetModel)
            .where(DatasetModel.deleted_at.is_(None))
            .order_by(DatasetModel.created_at.desc())
        )
        return [dataset_to_domain(m) for m in self._session.scalars(query).all()]

    def get_next_version(self) -> int:
        result = self._session.scalar(select(func.max(DatasetModel.version)))
        return (result or 0) + 1

    def update(self, entity: Dataset) -> Dataset:
        model = self._session.get(DatasetModel, str(entity.id))
        if model is None:
            raise LookupError("Dataset not found.")
        model.name = entity.name
        model.status = entity.status.value
        model.fingerprint_count = entity.fingerprint_count
        model.observation_count = entity.observation_count
        model.floor_count = entity.floor_count
        model.dataset_version = entity.dataset_version
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return dataset_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(DatasetModel, str(entity_id))
        if model is None:
            raise LookupError("Dataset not found.")
        entity = dataset_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
