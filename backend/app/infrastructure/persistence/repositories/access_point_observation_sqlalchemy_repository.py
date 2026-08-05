from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.access_point_observation import AccessPointObservation
from app.infrastructure.persistence.models import AccessPointObservationModel
from app.infrastructure.persistence.repositories.mappers import access_point_observation_to_domain


class SqlAlchemyAccessPointObservationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: AccessPointObservation) -> AccessPointObservation:
        model = AccessPointObservationModel(
            id=str(entity.id),
            fingerprint_id=str(entity.fingerprint_id),
            bssid=entity.bssid,
            ssid=entity.ssid,
            rssi=entity.rssi,
            frequency=entity.frequency,
            channel=entity.channel,
            band=entity.band,
            security=entity.security,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return access_point_observation_to_domain(model)

    def get(self, entity_id: UUID) -> AccessPointObservation | None:
        model = self._session.get(AccessPointObservationModel, str(entity_id))
        return access_point_observation_to_domain(model) if model else None

    def list_by_fingerprint(self, fingerprint_id: UUID) -> list[AccessPointObservation]:
        query = (
            select(AccessPointObservationModel)
            .where(
                AccessPointObservationModel.fingerprint_id == str(fingerprint_id),
                AccessPointObservationModel.deleted_at.is_(None),
            )
            .order_by(AccessPointObservationModel.bssid)
        )
        return [access_point_observation_to_domain(m) for m in self._session.scalars(query).all()]

    def update(self, entity: AccessPointObservation) -> AccessPointObservation:
        model = self._session.get(AccessPointObservationModel, str(entity.id))
        if model is None:
            raise LookupError("AccessPointObservation not found.")
        model.bssid = entity.bssid
        model.ssid = entity.ssid
        model.rssi = entity.rssi
        model.frequency = entity.frequency
        model.channel = entity.channel
        model.band = entity.band
        model.security = entity.security
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return access_point_observation_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(AccessPointObservationModel, str(entity_id))
        if model is None:
            raise LookupError("AccessPointObservation not found.")
        entity = access_point_observation_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
