from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.entities.access_point_observation import AccessPointObservation
from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.entities.fingerprint import Fingerprint
from app.domain.errors import BusinessRuleViolation, DomainValidationError
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.access_point_observation_repository import AccessPointObservationRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cell_repository import CellRepository
from app.repositories.fingerprint_repository import FingerprintRepository


class FingerprintService:
    def __init__(
        self,
        fingerprint_repository: FingerprintRepository,
        campaign_repository: CampaignRepository,
        cell_repository: CellRepository,
        observation_repository: AccessPointObservationRepository,
    ) -> None:
        self._fingerprint_repo = fingerprint_repository
        self._campaign_repo = campaign_repository
        self._cell_repo = cell_repository
        self._observation_repo = observation_repository

    def list_by_campaign(self, campaign_id: UUID) -> list[Fingerprint]:
        self._require_campaign_active(campaign_id)
        return self._fingerprint_repo.list_by_campaign(campaign_id)

    def count_by_campaign(self, campaign_id: UUID) -> int:
        self._require_campaign_active(campaign_id)
        return self._fingerprint_repo.count_by_campaign(campaign_id)

    def get(self, fingerprint_id: UUID) -> Fingerprint:
        fp = self._fingerprint_repo.get(fingerprint_id)
        if fp is None:
            raise LookupError("Fingerprint not found.")
        return fp

    def delete(self, fingerprint_id: UUID, deleted_by: UUID | None = None) -> None:
        fp = self.get(fingerprint_id)
        campaign = self._campaign_repo.get(fp.campaign_id)
        if campaign is not None and campaign.status in (
            CampaignStatus.COMPLETED,
            CampaignStatus.ARCHIVED,
        ):
            raise BusinessRuleViolation(
                f"Cannot delete fingerprints from a {campaign.status.value.lower()} campaign."
            )
        self._fingerprint_repo.soft_delete(fingerprint_id, deleted_by)

    def create(
        self,
        campaign_id: UUID,
        cell_id: UUID,
        device_id: str,
        captured_at: datetime,
        sample_number: int,
        orientation: float = 0.0,
        notes: str | None = None,
        observations: list[dict[str, Any]] | None = None,
    ) -> Fingerprint:
        campaign = self._require_campaign_active(campaign_id)
        if not campaign.accepts_fingerprints:
            raise BusinessRuleViolation(
                f"Campaign does not accept fingerprints in status {campaign.status.value}."
            )
        cell = self._cell_repo.get(cell_id)
        if cell is None or not cell.is_active:
            raise LookupError("Cell not found or inactive.")
        if observations is not None and len(observations) == 0:
            raise DomainValidationError(
                "Fingerprint must have at least one AccessPointObservation."
            )

        fingerprint = Fingerprint(
            campaign_id=campaign_id,
            cell_id=cell_id,
            device_id=device_id,
            captured_at=captured_at,
            sample_number=sample_number,
            orientation=orientation,
            notes=notes,
        )
        saved = self._fingerprint_repo.add(fingerprint)
        EventBus.publish(DomainEvent(EventType.FINGERPRINT_CAPTURED, saved.id, {
            "campaign_id": str(campaign_id),
            "cell_id": str(cell_id),
            "observation_count": len(observations) if observations else 0,
        }))

        if observations:
            for obs in observations:
                self._add_observation(saved.id, obs)

        return saved

    def get_observations(self, fingerprint_id: UUID) -> list[AccessPointObservation]:
        self.get(fingerprint_id)
        return self._observation_repo.list_by_fingerprint(fingerprint_id)

    def _require_campaign_active(self, campaign_id: UUID) -> "Campaign":
        campaign = self._campaign_repo.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found.")
        return campaign

    def _add_observation(self, fingerprint_id: UUID, obs: dict[str, Any]) -> AccessPointObservation:
        entity = AccessPointObservation(
            fingerprint_id=fingerprint_id,
            bssid=obs.get("bssid", ""),
            ssid=obs.get("ssid", ""),
            rssi=obs.get("rssi", 0),
            frequency=obs.get("frequency", 0),
            channel=obs.get("channel", 0),
            band=obs.get("band", ""),
            security=obs.get("security", ""),
        )
        return self._observation_repo.add(entity)
