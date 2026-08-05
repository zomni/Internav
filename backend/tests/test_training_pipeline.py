import json

import pytest

from app.domain.events import EventBus
from tests.conftest import auth_header, login_admin
from tests.floorplan import upload_floor_plan


def _create_org(client, token):
    return client.post(
        "/api/v1/organizations",
        json={"name": "Org", "code": "ORG"},
        headers=auth_header(token),
    ).json()["data"]


def _create_site(client, token, org_id):
    return client.post(
        "/api/v1/sites",
        json={"organization_id": org_id, "name": "Site", "code": "SIT", "timezone": "UTC"},
        headers=auth_header(token),
    ).json()["data"]


def _create_building(client, token, site_id):
    return client.post(
        "/api/v1/buildings",
        json={"site_id": site_id, "name": "Building", "code": "BLD"},
        headers=auth_header(token),
    ).json()["data"]


def _create_floor(client, token, building_id):
    return client.post(
        "/api/v1/floors",
        json={"building_id": building_id, "name": "Floor", "level": 0, "display_order": 1},
        headers=auth_header(token),
    ).json()["data"]


def _create_floor_plan(client, token, floor_id):
    return upload_floor_plan(client, token, floor_id)


def _create_grid(client, token, floor_id):
    _create_floor_plan(client, token, floor_id)
    return client.post(
        f"/api/v1/floors/{floor_id}/grids",
        json={"name": "Grid", "cell_size": 3},
        headers=auth_header(token),
    ).json()["data"]


def _get_walkable_cells(client, token, grid_id):
    resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    return [c for c in resp.json()["data"] if c["walkable"]]


def _add_fingerprint(client, token, campaign_id, cell_id, bssid, rssi):
    return client.post(
        f"/api/v1/campaigns/{campaign_id}/fingerprints",
        json={
            "cell_id": cell_id,
            "device_id": "TRAIN-DEVICE",
            "captured_at": "2026-07-28T12:00:00Z",
            "sample_number": 1,
            "observations": [{"bssid": bssid, "ssid": "", "rssi": rssi, "frequency": 2412}],
        },
        headers=auth_header(token),
    ).json()["data"]


@pytest.fixture(autouse=True)
def reset_events():
    EventBus.reset()


class TestTrainEndpoint:
    def _setup_complete_scenario(self, client, token):
        org = _create_org(client, token)
        site = _create_site(client, token, org["id"])
        bld = _create_building(client, token, site["id"])
        floor = _create_floor(client, token, bld["id"])

        grid = _create_grid(client, token, floor["id"])
        cells = _get_walkable_cells(client, token, grid["id"])
        assert len(cells) >= 2

        # Create campaign with fingerprints for at least 2 cells
        resp = client.post(
            f"/api/v1/floors/{floor['id']}/campaigns",
            json={"name": "Train Campaign"},
            headers=auth_header(token),
        )
        camp = resp.json()["data"]
        cid = camp["id"]
        client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
        client.patch(f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token))

        _add_fingerprint(client, token, cid, cells[0]["id"], "AA:BB:CC:DD:EE:01", -45)
        _add_fingerprint(client, token, cid, cells[0]["id"], "AA:BB:CC:DD:EE:01", -50)
        _add_fingerprint(client, token, cid, cells[1]["id"], "AA:BB:CC:DD:EE:02", -60)
        _add_fingerprint(client, token, cid, cells[1]["id"], "AA:BB:CC:DD:EE:02", -55)
        _add_fingerprint(client, token, cid, cells[0]["id"], "AA:BB:CC:DD:EE:01", -48)

        client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))

        # Build dataset
        resp = client.post(
            "/api/v1/datasets",
            json={"name": "Train Dataset"},
            headers=auth_header(token),
        )
        ds = resp.json()["data"]
        dsid = ds["id"]
        client.patch(
            f"/api/v1/datasets/{dsid}/add-campaigns",
            json={"campaign_ids": [cid]},
            headers=auth_header(token),
        )
        client.patch(f"/api/v1/datasets/{dsid}/build", headers=auth_header(token))
        dataset = client.get(f"/api/v1/datasets/{dsid}", headers=auth_header(token)).json()["data"]

        return floor, dataset

    def test_train_endpoint_success(self, client, seed_admin):
        token = login_admin(client)
        floor, dataset = self._setup_complete_scenario(client, token)

        # Create model version
        resp = client.post(
            "/api/v1/models",
            json={
                "dataset_id": dataset["id"],
                "floor_id": floor["id"],
                "algorithm": "knn",
            },
            headers=auth_header(token),
        )
        mv_id = resp.json()["data"]["id"]

        # Train
        resp = client.post(
            f"/api/v1/models/{mv_id}/train",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "Ready"
        assert data["training_time"] is not None
        assert data["checksum"] is not None
        assert data["metrics"] is not None

        metrics = json.loads(data["metrics"])
        assert "accuracy" in metrics
        assert "macro_f1" in metrics
        assert "per_class" in metrics

    def test_train_missing_model_returns_404(self, client, seed_admin):
        token = login_admin(client)
        resp = client.post(
            "/api/v1/models/00000000-0000-0000-0000-000000000000/train",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_train_empty_dataset_returns_409_and_marks_failed(self, client, seed_admin):
        token = login_admin(client)
        org = _create_org(client, token)
        site = _create_site(client, token, org["id"])
        bld = _create_building(client, token, site["id"])
        floor = _create_floor(client, token, bld["id"])

        dsid = client.post(
            "/api/v1/datasets",
            json={"name": "Empty Dataset"},
            headers=auth_header(token),
        ).json()["data"]["id"]

        mv_id = client.post(
            "/api/v1/models",
            json={"dataset_id": dsid, "floor_id": floor["id"], "algorithm": "knn"},
            headers=auth_header(token),
        ).json()["data"]["id"]

        resp = client.post(f"/api/v1/models/{mv_id}/train", headers=auth_header(token))
        assert resp.status_code == 409
        assert "Training failed" in resp.json()["detail"]

        mv = client.get(f"/api/v1/models/{mv_id}", headers=auth_header(token)).json()["data"]
        assert mv["status"] == "Failed"

    def test_download_after_train_succeeds(self, client, seed_admin):
        token = login_admin(client)
        floor, dataset = self._setup_complete_scenario(client, token)

        resp = client.post(
            "/api/v1/models",
            json={
                "dataset_id": dataset["id"],
                "floor_id": floor["id"],
                "algorithm": "knn",
            },
            headers=auth_header(token),
        )
        mv_id = resp.json()["data"]["id"]

        client.post(f"/api/v1/models/{mv_id}/train", headers=auth_header(token))

        resp = client.get(
            f"/api/v1/models/{mv_id}/download",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"

    def test_mobile_bundle_after_train(self, client, seed_admin):
        import hashlib

        token = login_admin(client)
        floor, dataset = self._setup_complete_scenario(client, token)

        resp = client.post(
            "/api/v1/models",
            json={
                "dataset_id": dataset["id"],
                "floor_id": floor["id"],
                "algorithm": "knn",
            },
            headers=auth_header(token),
        )
        mv_id = resp.json()["data"]["id"]

        client.post(f"/api/v1/models/{mv_id}/train", headers=auth_header(token))

        resp = client.get(
            f"/api/v1/models/{mv_id}/mobile-bundle",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert resp.headers["x-model-checksum"] == hashlib.sha256(resp.content).hexdigest()

        data = resp.json()
        assert "feature_schema" in data
        assert "references" in data
        assert len(data["references"]) >= 1
        assert "bssid_vocabulary" in data["feature_schema"]
        assert "classes" in data["feature_schema"]
        for ref in data["references"]:
            assert ref["cell_id"] is not None
            assert len(ref["vector"]) == len(data["feature_schema"]["bssid_vocabulary"])

    def test_mobile_bundle_before_train_returns_409(self, client, seed_admin):
        token = login_admin(client)
        floor, dataset = self._setup_complete_scenario(client, token)

        resp = client.post(
            "/api/v1/models",
            json={
                "dataset_id": dataset["id"],
                "floor_id": floor["id"],
                "algorithm": "knn",
            },
            headers=auth_header(token),
        )
        mv_id = resp.json()["data"]["id"]

        resp = client.get(
            f"/api/v1/models/{mv_id}/mobile-bundle",
            headers=auth_header(token),
        )
        assert resp.status_code == 409

    def test_mobile_bundle_missing_model_returns_404(self, client, seed_admin):
        token = login_admin(client)
        resp = client.get(
            "/api/v1/models/00000000-0000-0000-0000-000000000000/mobile-bundle",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_train_rbac_requires_auth(self, client, seed_admin):
        token = login_admin(client)
        floor, dataset = self._setup_complete_scenario(client, token)
        resp = client.post(
            "/api/v1/models",
            json={
                "dataset_id": dataset["id"],
                "floor_id": floor["id"],
                "algorithm": "knn",
            },
            headers=auth_header(token),
        )
        mv_id = resp.json()["data"]["id"]

        resp = client.post(f"/api/v1/models/{mv_id}/train")
        assert resp.status_code == 401
