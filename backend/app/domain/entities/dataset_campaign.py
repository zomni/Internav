from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity


@dataclass(kw_only=True)
class DatasetCampaign(AuditableEntity):
    dataset_id: UUID
    campaign_id: UUID
