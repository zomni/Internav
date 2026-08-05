from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.fingerprint import Fingerprint
from app.infrastructure.persistence.models import CampaignModel, FingerprintModel
from app.infrastructure.persistence.repositories.mappers import fingerprint_to_domain


class SqlAlchemyFingerprintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Fingerprint) -> Fingerprint:
        model = FingerprintModel(
            id=str(entity.id),
            campaign_id=str(entity.campaign_id),
            cell_id=str(entity.cell_id),
            device_id=entity.device_id,
            captured_at=entity.captured_at,
            sample_number=entity.sample_number,
            orientation=entity.orientation,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return fingerprint_to_domain(model)

    def get(self, entity_id: UUID) -> Fingerprint | None:
        model = self._session.get(FingerprintModel, str(entity_id))
        return fingerprint_to_domain(model) if model else None

    def list_by_campaign(self, campaign_id: UUID) -> list[Fingerprint]:
        query = (
            select(FingerprintModel)
            .where(
                FingerprintModel.campaign_id == str(campaign_id),
                FingerprintModel.deleted_at.is_(None),
            )
            .order_by(FingerprintModel.captured_at.desc())
        )
        return [fingerprint_to_domain(m) for m in self._session.scalars(query).all()]

    def list_by_floor(self, floor_id: UUID) -> list[Fingerprint]:
        query = (
            select(FingerprintModel)
            .join(CampaignModel, FingerprintModel.campaign_id == CampaignModel.id)
            .where(
                CampaignModel.floor_id == str(floor_id),
                FingerprintModel.deleted_at.is_(None),
                CampaignModel.deleted_at.is_(None),
            )
            .order_by(FingerprintModel.captured_at.desc())
        )
        return [fingerprint_to_domain(m) for m in self._session.scalars(query).all()]

    def count_by_campaign(self, campaign_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(FingerprintModel)
            .where(
                FingerprintModel.campaign_id == str(campaign_id),
                FingerprintModel.deleted_at.is_(None),
            )
        )
        return self._session.scalar(query) or 0

    def update(self, entity: Fingerprint) -> Fingerprint:
        model = self._session.get(FingerprintModel, str(entity.id))
        if model is None:
            raise LookupError("Fingerprint not found.")
        model.campaign_id = str(entity.campaign_id)
        model.cell_id = str(entity.cell_id)
        model.device_id = entity.device_id
        model.captured_at = entity.captured_at
        model.sample_number = entity.sample_number
        model.orientation = entity.orientation
        model.notes = entity.notes
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return fingerprint_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(FingerprintModel, str(entity_id))
        if model is None:
            raise LookupError("Fingerprint not found.")
        entity = fingerprint_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
