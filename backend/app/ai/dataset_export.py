"""Export datasets to training-ready format."""
from typing import Any
from uuid import UUID

from app.domain.entities.base import utc_now
from app.repositories.access_point_observation_repository import AccessPointObservationRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cell_repository import CellRepository
from app.repositories.dataset_campaign_repository import DatasetCampaignRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.fingerprint_repository import FingerprintRepository


class DatasetExportService:
    def __init__(
        self,
        dataset_repository: DatasetRepository,
        dataset_campaign_repository: DatasetCampaignRepository,
        campaign_repository: CampaignRepository,
        fingerprint_repository: FingerprintRepository,
        observation_repository: AccessPointObservationRepository,
        cell_repository: CellRepository,
    ) -> None:
        self._dataset_repo = dataset_repository
        self._dataset_campaign_repo = dataset_campaign_repository
        self._campaign_repo = campaign_repository
        self._fingerprint_repo = fingerprint_repository
        self._obs_repo = observation_repository
        self._cell_repo = cell_repository

    def export_dataset(self, dataset_id: UUID) -> dict[str, Any]:
        dataset = self._dataset_repo.get(dataset_id)
        if dataset is None:
            raise LookupError("Dataset not found.")

        campaign_ids = self._dataset_campaign_repo.list_campaign_ids(dataset_id)
        samples: list[dict[str, Any]] = []
        unique_bssids: set[str] = set()

        for cid in campaign_ids:
            campaign = self._campaign_repo.get(cid)
            if campaign is None:
                continue
            fingerprints = self._fingerprint_repo.list_by_campaign(cid)
            for fp in fingerprints:
                obs_list = self._obs_repo.list_by_fingerprint(fp.id)
                cell = self._cell_repo.get(fp.cell_id)
                sample = {
                    "fingerprint_id": str(fp.id),
                    "campaign_id": str(cid),
                    "cell_id": str(fp.cell_id),
                    "device_id": fp.device_id,
                    "captured_at": fp.captured_at.isoformat(),
                    "cell_center_x": cell.center_x if cell else 0.0,
                    "cell_center_y": cell.center_y if cell else 0.0,
                    "cell_row": cell.row if cell else 0,
                    "cell_column": cell.column if cell else 0,
                    "observations": [
                        {
                            "bssid": obs.bssid,
                            "ssid": obs.ssid,
                            "rssi": obs.rssi,
                            "frequency": obs.frequency,
                        }
                        for obs in obs_list
                    ],
                }
                for obs in obs_list:
                    unique_bssids.add(obs.bssid)
                samples.append(sample)

        export = {
            "dataset_id": str(dataset_id),
            "dataset_name": dataset.name,
            "dataset_version": dataset.dataset_version,
            "floor_ids": list({str(campaign.floor_id) for cid in campaign_ids if (campaign := self._campaign_repo.get(cid))}),
            "samples": samples,
            "bssid_vocabulary": sorted(unique_bssids),
            "exported_at": utc_now().isoformat(),
        }
        return export
