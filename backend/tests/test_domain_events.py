from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.application.campaign_service import CampaignService
from app.application.core_hierarchy_service import CoreHierarchyService
from app.application.dataset_service import DatasetService
from app.application.fingerprint_service import FingerprintService
from app.application.model_update_service import ModelUpdateService
from app.application.model_version_service import ModelVersionService
from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.entities.cell import Cell
from app.domain.entities.dataset import Dataset
from app.domain.entities.fingerprint import Fingerprint
from app.domain.entities.floor import Floor
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.entities.organization import Organization
from app.domain.entities.site import Site
from app.domain.events import DomainEvent, EventBus, EventType
from app.infrastructure.events.audit_listeners import subscribe_audit_listeners
from tests.conftest import auth_header, login_admin

_TEST_FLOOR_ID = uuid4()


class FakeModelVersionRepo:
    def __init__(self):
        self._models: dict[UUID, ModelVersion] = {}

    def get(self, model_version_id: UUID) -> ModelVersion | None:
        return self._models.get(model_version_id)

    def list_by_floor(self, floor_id: UUID) -> list[ModelVersion]:
        return [m for m in self._models.values() if m.floor_id == floor_id]

    def get_published_on_floor(self, floor_id: UUID) -> ModelVersion | None:
        for m in self._models.values():
            if m.floor_id == floor_id and m.status == ModelVersionStatus.PUBLISHED:
                return m
        return None

    def add(self, mv: ModelVersion) -> ModelVersion:
        self._models[mv.id] = mv
        return mv

    def update(self, mv: ModelVersion) -> ModelVersion:
        self._models[mv.id] = mv
        return mv

    def has_published_on_floor(self, floor_id: UUID) -> bool:
        return any(
            m.floor_id == floor_id and m.status == ModelVersionStatus.PUBLISHED
            for m in self._models.values()
        )


class FakeFloorRepo:
    def __init__(self):
        self._floors: dict[UUID, Floor] = {}

    def get(self, floor_id: UUID) -> Floor | None:
        return self._floors.get(floor_id)

    def add(self, f: Floor) -> Floor:
        self._floors[f.id] = f
        return f


class FakeCampaignRepo:
    def __init__(self):
        self._data: dict[UUID, Campaign] = {}

    def get(self, cid: UUID) -> Campaign | None:
        return self._data.get(cid)

    def add(self, c: Campaign) -> Campaign:
        self._data[c.id] = c
        return c

    def update(self, c: Campaign) -> Campaign:
        self._data[c.id] = c
        return c

    def list_by_floor(self, floor_id: UUID) -> list[Campaign]:
        return [c for c in self._data.values() if c.floor_id == floor_id]


class FakeFingerprintRepo:
    def __init__(self):
        self._data: dict[UUID, Fingerprint] = {}

    def get(self, fid: UUID) -> Fingerprint | None:
        return self._data.get(fid)

    def add(self, f: Fingerprint) -> Fingerprint:
        self._data[f.id] = f
        return f

    def list_by_campaign(self, campaign_id: UUID) -> list[Fingerprint]:
        return [f for f in self._data.values() if f.campaign_id == campaign_id]

    def count_by_campaign(self, campaign_id: UUID) -> int:
        return sum(1 for f in self._data.values() if f.campaign_id == campaign_id)

    def list_by_floor(self, floor_id: UUID) -> list[Fingerprint]:
        return []


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

    def add(self, obs) -> object:
        return obs

    def list_by_fingerprint(self, fingerprint_id: UUID) -> list:
        return []


class FakeDatasetRepo:
    def __init__(self):
        self._data: dict[UUID, Dataset] = {}

    def get(self, did: UUID) -> Dataset | None:
        return self._data.get(did)

    def add(self, d: Dataset) -> Dataset:
        self._data[d.id] = d
        return d

    def update(self, d: Dataset) -> Dataset:
        self._data[d.id] = d
        return d

    def list_all(self) -> list[Dataset]:
        return list(self._data.values())


class FakeDatasetCampaignRepo:
    def __init__(self):
        self._data: list = []

    def add(self, dc) -> object:
        self._data.append(dc)
        return dc

    def list_campaign_ids(self, dataset_id: UUID) -> list[UUID]:
        return [dc.campaign_id for dc in self._data if dc.dataset_id == dataset_id]

    def list_by_dataset(self, dataset_id: UUID) -> list:
        return [dc for dc in self._data if dc.dataset_id == dataset_id]


class FakeOrgRepo:
    def __init__(self):
        self._data: dict[UUID, Organization] = {}

    def get(self, oid: UUID) -> Organization | None:
        return self._data.get(oid)

    def add(self, o: Organization) -> Organization:
        self._data[o.id] = o
        return o

    def update(self, o: Organization) -> Organization:
        self._data[o.id] = o
        return o

    def list_all(self, is_active: bool | None = None) -> list[Organization]:
        return list(self._data.values())

    def soft_delete(self, oid: UUID) -> None:
        pass


class FakeSiteRepo:
    def get(self, sid: UUID) -> Site | None:
        return None

    def add(self, s: Site) -> Site:
        return s

    def update(self, s: Site) -> Site:
        return s

    def list_all(self, is_active: bool | None = None) -> list[Site]:
        return []

    def soft_delete(self, sid: UUID) -> None:
        pass


class FakeBuildingRepo:
    def get(self, bid: UUID) -> None:
        return None

    def add(self, b) -> object:
        return b

    def update(self, b) -> object:
        return b

    def list_all(self, is_active: bool | None = None) -> list:
        return []

    def soft_delete(self, bid: UUID) -> None:
        pass


# ---------- Event Publication Tests ----------


class TestEventPublications:
    def setup_method(self):
        EventBus.reset()

    def test_organization_created_publishes_event(self):
        org_repo = FakeOrgRepo()
        service = CoreHierarchyService(org_repo, FakeSiteRepo(), FakeBuildingRepo(), FakeFloorRepo())
        received: list[DomainEvent] = []
        EventBus.subscribe(EventType.ORGANIZATION_CREATED, lambda e: received.append(e))
        org = service.create_organization(name="Test", code="T", description=None)
        assert len(received) == 1
        assert received[0].event_type == EventType.ORGANIZATION_CREATED
        assert received[0].entity_id == org.id

    def test_campaign_started_publishes_event(self):
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        campaign_repo = FakeCampaignRepo()
        service = CampaignService(campaign_repo, floor_repo)
        campaign = service.create(floor_id=floor.id, name="Test Campaign")
        service.start(campaign.id)
        received: list[DomainEvent] = []
        EventBus.subscribe(EventType.CAMPAIGN_STARTED, lambda e: received.append(e))
        service.begin_collecting(campaign.id)
        assert len(received) == 1
        assert received[0].event_type == EventType.CAMPAIGN_STARTED
        assert received[0].entity_id == campaign.id

    def test_fingerprint_captured_publishes_event(self):
        campaign_repo = FakeCampaignRepo()
        campaign = Campaign(floor_id=_TEST_FLOOR_ID, name="Test")
        campaign.transition_to(CampaignStatus.READY)
        campaign.transition_to(CampaignStatus.COLLECTING)
        campaign_repo.add(campaign)
        cell_repo = FakeCellRepo()
        cell = Cell(grid_id=uuid4(), row=0, column=0, center_x=0.0, center_y=0.0)
        cell.is_active = True
        cell_repo.add(cell)
        service = FingerprintService(FakeFingerprintRepo(), campaign_repo, cell_repo, FakeObservationRepo())
        received: list[DomainEvent] = []
        EventBus.subscribe(EventType.FINGERPRINT_CAPTURED, lambda e: received.append(e))
        fp = service.create(
            campaign_id=campaign.id,
            cell_id=cell.id,
            device_id="dev1",
            captured_at=datetime.now(UTC),
            sample_number=1,
            observations=[{"bssid": "aa:bb", "ssid": "net", "rssi": -50, "frequency": 2400}],
        )
        assert len(received) == 1
        assert received[0].event_type == EventType.FINGERPRINT_CAPTURED
        assert received[0].entity_id == fp.id

    def test_dataset_built_publishes_event(self):
        campaign_repo = FakeCampaignRepo()
        campaign = Campaign(floor_id=_TEST_FLOOR_ID, name="Test")
        campaign.transition_to(CampaignStatus.READY)
        campaign.transition_to(CampaignStatus.COLLECTING)
        campaign.transition_to(CampaignStatus.COMPLETED)
        campaign_repo.add(campaign)
        service = DatasetService(
            FakeDatasetRepo(), FakeDatasetCampaignRepo(), campaign_repo,
            FakeFingerprintRepo(), FakeCellRepo(),
        )
        ds = service.create("Test DS")
        service.add_campaigns(ds.id, [campaign.id])
        received: list[DomainEvent] = []
        EventBus.subscribe(EventType.DATASET_BUILT, lambda e: received.append(e))
        service.build(ds.id)
        assert len(received) == 1
        assert received[0].event_type == EventType.DATASET_BUILT
        assert received[0].entity_id == ds.id

    def test_model_published_publishes_event(self):
        mv_repo = FakeModelVersionRepo()
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        dataset_repo = FakeDatasetRepo()
        ds = Dataset(name="Test")
        dataset_repo.add(ds)
        service = ModelVersionService(mv_repo, dataset_repo, floor_repo)
        mv = service.create(dataset_id=ds.id, floor_id=floor.id, algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv_repo.update(mv)
        received: list[DomainEvent] = []
        EventBus.subscribe(EventType.MODEL_PUBLISHED, lambda e: received.append(e))
        service.publish(mv.id)
        assert len(received) == 1
        assert received[0].event_type == EventType.MODEL_PUBLISHED
        assert received[0].entity_id == mv.id

    def test_multiple_listeners_receive_same_event(self):
        EventBus.reset()
        org_repo = FakeOrgRepo()
        service = CoreHierarchyService(org_repo, FakeSiteRepo(), FakeBuildingRepo(), FakeFloorRepo())
        received: list[str] = []
        EventBus.subscribe(EventType.ORGANIZATION_CREATED, lambda e: received.append("a"))
        EventBus.subscribe(EventType.ORGANIZATION_CREATED, lambda e: received.append("b"))
        service.create_organization(name="Multi", code="M", description=None)
        assert sorted(received) == ["a", "b"]


# ---------- ModelUpdateService Tests ----------


class TestModelUpdateService:
    def setup_method(self):
        EventBus.reset()

    def test_no_published_model_returns_no_update(self):
        mv_repo = FakeModelVersionRepo()
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        service = ModelUpdateService(mv_repo, floor_repo)
        result = service.check_for_update(floor.id)
        assert result["update_available"] is False
        assert result["model"] is None

    def test_returns_update_when_published_model_exists(self):
        mv_repo = FakeModelVersionRepo()
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        mv = ModelVersion(dataset_id=uuid4(), floor_id=floor.id, algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv_repo.add(mv)
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        mv_repo.update(mv)
        service = ModelUpdateService(mv_repo, floor_repo)
        result = service.check_for_update(floor.id)
        assert result["update_available"] is True
        assert result["model"]["id"] == str(mv.id)

    def test_no_update_when_current_version_matches(self):
        mv_repo = FakeModelVersionRepo()
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        mv = ModelVersion(dataset_id=uuid4(), floor_id=floor.id, algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv_repo.add(mv)
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        mv_repo.update(mv)
        service = ModelUpdateService(mv_repo, floor_repo)
        result = service.check_for_update(floor.id, current_model_version_id=str(mv.id))
        assert result["update_available"] is False

    def test_raises_on_missing_floor(self):
        service = ModelUpdateService(FakeModelVersionRepo(), FakeFloorRepo())
        with pytest.raises(LookupError):
            service.check_for_update(uuid4())

    def test_get_published_model_returns_none_when_missing(self):
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        service = ModelUpdateService(FakeModelVersionRepo(), floor_repo)
        assert service.get_published_model(floor.id) is None

    def test_get_published_model_returns_model(self):
        mv_repo = FakeModelVersionRepo()
        floor_repo = FakeFloorRepo()
        floor = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        floor_repo.add(floor)
        mv = ModelVersion(dataset_id=uuid4(), floor_id=floor.id, algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv_repo.add(mv)
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        mv_repo.update(mv)
        service = ModelUpdateService(mv_repo, floor_repo)
        result = service.get_published_model(floor.id)
        assert result is not None
        assert result.id == mv.id


# ---------- Audit Listeners Tests ----------


class TestAuditListeners:
    def setup_method(self):
        EventBus.reset()

    def test_subscribe_audit_listeners_wires_all_events(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.ORGANIZATION_CREATED, uuid4(), {"name": "Test"}))
        assert "Organization created" in caplog.text

    def test_campaign_started_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.CAMPAIGN_STARTED, uuid4(), {"floor_id": str(uuid4())}))
        assert "Campaign started" in caplog.text

    def test_fingerprint_captured_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        eid = uuid4()
        EventBus.publish(DomainEvent(EventType.FINGERPRINT_CAPTURED, eid, {"campaign_id": str(uuid4()), "cell_id": str(uuid4())}))
        assert "Fingerprint captured" in caplog.text
        assert str(eid) in caplog.text

    def test_dataset_built_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.DATASET_BUILT, uuid4(), {"fingerprint_count": 10, "floor_count": 2}))
        assert "Dataset built" in caplog.text

    def test_training_started_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.TRAINING_STARTED, uuid4()))
        assert "Training started" in caplog.text

    def test_training_completed_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.TRAINING_COMPLETED, uuid4(), {"metrics": {"accuracy": 0.95}}))
        assert "Training completed" in caplog.text

    def test_model_ready_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.MODEL_READY, uuid4()))
        assert "Model ready" in caplog.text

    def test_model_published_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.MODEL_PUBLISHED, uuid4(), {"floor_id": str(uuid4()), "algorithm": "knn"}))
        assert "Model published" in caplog.text

    def test_model_downloaded_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.MODEL_DOWNLOADED, uuid4()))
        assert "Model downloaded" in caplog.text

    def test_inference_executed_audit_log(self, caplog):
        subscribe_audit_listeners()
        caplog.set_level(10, logger="audit.events")
        EventBus.publish(DomainEvent(EventType.INFERENCE_EXECUTED, uuid4(), {"predicted_cell_id": "cell1", "confidence": 0.85}))
        assert "Inference executed" in caplog.text


# ---------- Model Update API Integration Tests ----------


class TestModelUpdateAPI:
    def _setup_floor(self, client: TestClient, token: str) -> dict:
        org_resp = client.post("/api/v1/organizations", json={"name": "Org", "code": "ORG"}, headers=auth_header(token))
        assert org_resp.status_code == 201, org_resp.text
        org = org_resp.json()["data"]
        site_resp = client.post("/api/v1/sites", json={"organization_id": org["id"], "name": "S", "code": "S", "timezone": "UTC"}, headers=auth_header(token))
        assert site_resp.status_code == 201, site_resp.text
        site = site_resp.json()["data"]
        building_resp = client.post("/api/v1/buildings", json={"site_id": site["id"], "name": "B", "code": "B"}, headers=auth_header(token))
        assert building_resp.status_code == 201, building_resp.text
        building = building_resp.json()["data"]
        floor_resp = client.post("/api/v1/floors", json={"building_id": building["id"], "name": "F1", "level": 0, "display_order": 1}, headers=auth_header(token))
        assert floor_resp.status_code == 201, floor_resp.text
        return floor_resp.json()["data"]

    def test_model_update_endpoint_returns_no_update_when_no_model(
        self, client: TestClient, seed_admin, settings
    ):
        token = login_admin(client)
        floor = self._setup_floor(client, token)
        resp = client.get(f"/api/v1/floors/{floor['id']}/model-update", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["update_available"] is False

    def test_model_update_endpoint_returns_update_when_published(
        self, client: TestClient, seed_admin, settings
    ):
        token = login_admin(client)
        floor = self._setup_floor(client, token)
        dataset_resp = client.post("/api/v1/datasets", json={"name": "DS"}, headers=auth_header(token))
        assert dataset_resp.status_code == 201, dataset_resp.text
        dataset = dataset_resp.json()["data"]
        model_resp = client.post("/api/v1/models", json={"dataset_id": dataset["id"], "floor_id": floor["id"], "algorithm": "knn"}, headers=auth_header(token))
        assert model_resp.status_code == 201, model_resp.text
        model = model_resp.json()["data"]
        ready_resp = client.patch(f"/api/v1/models/{model['id']}/mark-ready", json={}, headers=auth_header(token))
        assert ready_resp.status_code == 200, ready_resp.text
        publish_resp = client.patch(f"/api/v1/models/{model['id']}/publish", headers=auth_header(token))
        assert publish_resp.status_code == 200, publish_resp.text
        resp = client.get(f"/api/v1/floors/{floor['id']}/model-update", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["update_available"] is True
        assert data["model"]["id"] == model["id"]

    def test_model_update_requires_auth(self, client: TestClient):
        resp = client.get(f"/api/v1/floors/{uuid4()}/model-update")
        assert resp.status_code == 401
