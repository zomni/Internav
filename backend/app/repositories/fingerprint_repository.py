from uuid import UUID

from app.domain.entities.fingerprint import Fingerprint
from app.repositories.base import Repository


class FingerprintRepository(Repository[Fingerprint]):
    def list_by_campaign(self, campaign_id: UUID) -> list[Fingerprint]: ...

    def list_by_floor(self, floor_id: UUID) -> list[Fingerprint]: ...

    def count_by_campaign(self, campaign_id: UUID) -> int: ...
