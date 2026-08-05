from uuid import UUID

from app.domain.entities.access_point_observation import AccessPointObservation
from app.repositories.base import Repository


class AccessPointObservationRepository(Repository[AccessPointObservation]):
    def list_by_fingerprint(self, fingerprint_id: UUID) -> list[AccessPointObservation]: ...
