from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.inference_service import InferenceService, ObservationInput
from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.entities.cell import Cell
from app.domain.entities.fingerprint import Fingerprint
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.errors import DomainValidationError


class FakeModelVersionRepo:
    def __init__(self):
        self._data: dict[UUID, ModelVersion] = {}

    def get_published_on_floor(self, floor_id: UUID) -> ModelVersion | None:
        for mv in self._data.values():
            if mv.floor_id == floor_id and mv.status == ModelVersionStatus.PUBLISHED:
                return mv
        return None


class FakeFingerprintRepo:
    def __init__(self):
        self._data: dict[UUID, Fingerprint] = {}

    def add(self, fp: Fingerprint) -> Fingerprint:
        self._data[fp.id] = fp
        return fp

    def list_by_floor(self, floor_id: UUID) -> list[Fingerprint]:
        return [fp for fp in self._data.values()]


class FakeCellRepo:
    def __init__(self):
        self._data: dict[UUID, Cell] = {}

    def get(self, cid: UUID) -> Cell | None:
        return self._data.get(cid)

    def add(self, c: Cell) -> Cell:
        self._data[c.id] = c
        return c


class FakeObservationRepo:
    def __init__(self):
        self._data: dict = {}

    def list_by_fingerprint(self, fingerprint_id: UUID) -> list:
        return self._data.get(fingerprint_id, [])

    def set_observations(self, fingerprint_id: UUID, obs: list) -> None:
        self._data[fingerprint_id] = obs


def _make_observation(bssid: str, rssi: int = -50, ssid: str = "net", frequency: int = 2400) -> ObservationInput:
    return ObservationInput(bssid=bssid, ssid=ssid, rssi=rssi, frequency=frequency)


class TestInferenceService:
    def setup_method(self):
        self.mv_repo = FakeModelVersionRepo()
        self.fp_repo = FakeFingerprintRepo()
        self.cell_repo = FakeCellRepo()
        self.obs_repo = FakeObservationRepo()
        self.service = InferenceService(self.mv_repo, self.fp_repo, self.cell_repo, self.obs_repo)

    def _add_published_model(self, floor_id: UUID) -> ModelVersion:
        mv = ModelVersion(dataset_id=uuid4(), floor_id=floor_id, algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        self.mv_repo._data[mv.id] = mv
        return mv

    def _add_fingerprint(self, floor_id: UUID, cell_id: UUID, bssid: str, rssi: int = -50) -> Fingerprint:
        campaign = Campaign(floor_id=floor_id, name="Test")
        campaign.transition_to(CampaignStatus.READY)
        campaign.transition_to(CampaignStatus.COLLECTING)
        fp = Fingerprint(
            campaign_id=campaign.id,
            cell_id=cell_id,
            device_id="dev1",
            captured_at=datetime.now(UTC),
            sample_number=1,
        )
        self.fp_repo.add(fp)
        self.obs_repo.set_observations(fp.id, [type("Obs", (), {"bssid": bssid, "rssi": rssi})()])
        return fp

    def _add_cell(self, cell_id: UUID | None = None) -> Cell:
        cid = cell_id or uuid4()
        cell = Cell(grid_id=uuid4(), row=0, column=0, center_x=10.0, center_y=20.0)
        cell.id = cid
        self.cell_repo.add(cell)
        return cell

    def test_estimate_position_success(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        cell = self._add_cell()
        self._add_fingerprint(floor_id, cell.id, "aa:bb", -50)
        result = self.service.estimate_position(floor_id, [_make_observation("aa:bb", -50)])
        assert result.predicted_cell_id == str(cell.id)
        assert result.confidence > 0

    def test_raises_on_empty_observations(self):
        with pytest.raises(DomainValidationError, match="At least one observation"):
            self.service.estimate_position(uuid4(), [])

    def test_raises_on_no_published_model(self):
        with pytest.raises(LookupError, match="No published model"):
            self.service.estimate_position(uuid4(), [_make_observation("aa:bb")])

    def test_raises_on_no_matching_fingerprints(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        with pytest.raises(LookupError, match="No matching fingerprints"):
            self.service.estimate_position(floor_id, [_make_observation("aa:bb")])

    def test_raises_on_predicted_cell_not_found(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        missing_cell_id = uuid4()
        self._add_fingerprint(floor_id, missing_cell_id, "aa:bb", -50)
        with pytest.raises(LookupError, match="not found"):
            self.service.estimate_position(floor_id, [_make_observation("aa:bb")])

    def test_confidence_1_when_all_match_same_cell(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        cell = self._add_cell()
        self._add_fingerprint(floor_id, cell.id, "aa:bb", -50)
        self._add_fingerprint(floor_id, cell.id, "cc:dd", -50)
        result = self.service.estimate_position(floor_id, [
            _make_observation("aa:bb", -50),
            _make_observation("cc:dd", -50),
        ])
        assert result.confidence == 1.0

    def test_includes_model_version_id(self):
        floor_id = uuid4()
        mv = self._add_published_model(floor_id)
        cell = self._add_cell()
        self._add_fingerprint(floor_id, cell.id, "aa:bb", -50)
        result = self.service.estimate_position(floor_id, [_make_observation("aa:bb")])
        assert result.model_version_id == str(mv.id)

    def test_returns_top5_candidates(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        cells = [self._add_cell() for _ in range(6)]
        for c in cells:
            self._add_fingerprint(floor_id, c.id, str(c.id)[:8], -50)
        observations = [_make_observation(str(c.id)[:8], -50) for c in cells]
        result = self.service.estimate_position(floor_id, observations)
        assert len(result.candidate_cells) <= 5
        assert len(result.candidate_cells) > 0

    def test_inference_time_set(self):
        floor_id = uuid4()
        self._add_published_model(floor_id)
        cell = self._add_cell()
        self._add_fingerprint(floor_id, cell.id, "aa:bb", -50)
        result = self.service.estimate_position(floor_id, [_make_observation("aa:bb")])
        assert result.inference_time_ms > 0
