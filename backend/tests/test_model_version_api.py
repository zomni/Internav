from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin
from tests.floorplan import upload_floor_plan


def _create_org(client: TestClient, token: str) -> dict:
    resp = client.post(
        "/api/v1/organizations",
        json={"name": "Test Org", "code": "TST"},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_site(client: TestClient, token: str, org_id: str) -> dict:
    resp = client.post(
        "/api/v1/sites",
        json={
            "organization_id": org_id,
            "name": "Main Site",
            "code": "MAIN",
            "timezone": "America/Santiago",
        },
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_building(client: TestClient, token: str, site_id: str) -> dict:
    resp = client.post(
        "/api/v1/buildings",
        json={"site_id": site_id, "name": "North Wing", "code": "NW"},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_floor(client: TestClient, token: str, building_id: str) -> dict:
    resp = client.post(
        "/api/v1/floors",
        json={"building_id": building_id, "name": "Ground", "level": 0, "display_order": 1},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _setup_floor(client: TestClient, token: str) -> dict:
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    return _create_floor(client, token, building["id"])


def _create_floor_plan(client: TestClient, token: str, floor_id: str) -> dict:
    return upload_floor_plan(client, token, floor_id)


def _create_grid(client: TestClient, token: str, floor_id: str) -> dict:
    _create_floor_plan(client, token, floor_id)
    resp = client.post(
        f"/api/v1/floors/{floor_id}/grids",
        json={"name": "Main Grid", "cell_size": 3},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _get_walkable_cell(client: TestClient, token: str, grid_id: str) -> dict:
    resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    for cell in resp.json()["data"]:
        if cell["walkable"]:
            return cell
    raise AssertionError("No walkable cell found")


def _create_completed_campaign(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/campaigns",
        json={"name": "Completed Campaign"},
        headers=auth_header(token),
    )
    campaign = resp.json()["data"]
    cid = campaign["id"]
    client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    client.patch(f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token))
    grid = _create_grid(client, token, floor_id)
    cell = _get_walkable_cell(client, token, grid["id"])
    _add_fingerprint(client, token, cid, cell["id"])
    client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))
    return client.get(f"/api/v1/campaigns/{cid}", headers=auth_header(token)).json()["data"]


def _add_fingerprint(
    client: TestClient, token: str, campaign_id: str, cell_id: str
) -> dict:
    resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/fingerprints",
        json={
            "cell_id": cell_id,
            "device_id": "DEVICE-001",
            "captured_at": "2026-07-27T12:00:00Z",
            "sample_number": 1,
            "observations": [
                {
                    "bssid": "AA:BB:CC:DD:EE:01",
                    "ssid": "WiFi-1",
                    "rssi": -45,
                    "frequency": 2412,
                }
            ],
        },
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_ready_dataset(client: TestClient, token: str, floor_id: str) -> dict:
    _create_completed_campaign(client, token, floor_id)
    resp = client.post(
        "/api/v1/datasets",
        json={"name": "Training Dataset"},
        headers=auth_header(token),
    )
    dataset = resp.json()["data"]
    dsid = dataset["id"]
    resp = client.get(f"/api/v1/floors/{floor_id}/campaigns", headers=auth_header(token))
    campaigns = resp.json()["data"]
    completed_ids = [c["id"] for c in campaigns if c["status"] == "Completed"]
    if completed_ids:
        client.patch(
            f"/api/v1/datasets/{dsid}/add-campaigns",
            json={"campaign_ids": completed_ids},
            headers=auth_header(token),
        )
    client.patch(f"/api/v1/datasets/{dsid}/build", headers=auth_header(token))
    return client.get(f"/api/v1/datasets/{dsid}", headers=auth_header(token)).json()["data"]


# ── ModelVersion Create & List ──────────────────────────────────


def test_create_model_version(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["algorithm"] == "knn"
    assert data["status"] == "Training"
    assert data["version"] == 1


def test_list_models(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    resp = client.get("/api/v1/models", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


def test_get_model_version(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    resp = client.get(f"/api/v1/models/{mv_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == mv_id


def test_list_models_by_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    resp = client.get(f"/api/v1/floors/{floor['id']}/models", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


def test_create_model_version_missing_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": "00000000-0000-0000-0000-000000000000",
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 404


# ── State Transitions ───────────────────────────────────────────


def test_mark_ready(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/models/{mv_id}/mark-ready",
        json={"metrics": '{"accuracy": 0.95}', "training_time": 12.5},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Ready"
    assert resp.json()["data"]["metrics"] == '{"accuracy": 0.95}'


def test_mark_failed(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/models/{mv_id}/mark-failed",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Failed"


def test_invalid_transition(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    # Cannot go from Training directly to Published
    resp = client.patch(
        f"/api/v1/models/{mv_id}/publish",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Publish ─────────────────────────────────────────────────────


def test_publish(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/models/{mv_id}/publish",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "Published"
    assert data["published_at"] is not None


def test_only_one_published_per_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    # First model
    resp1 = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv1_id = resp1.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv1_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv1_id}/publish", headers=auth_header(token))
    # Second model
    resp2 = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "rf",
        },
        headers=auth_header(token),
    )
    mv2_id = resp2.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv2_id}/mark-ready", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/models/{mv2_id}/publish",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Unpublish / Archive ─────────────────────────────────────────


def test_unpublish_then_publish_new(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    # First model published
    resp1 = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv1_id = resp1.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv1_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv1_id}/publish", headers=auth_header(token))
    # Unpublish
    resp = client.patch(
        f"/api/v1/models/{mv1_id}/unpublish",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Archived"
    # Second model can now be published
    resp2 = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "rf",
        },
        headers=auth_header(token),
    )
    mv2_id = resp2.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv2_id}/mark-ready", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/models/{mv2_id}/publish",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Published"


def test_archive_ready_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/models/{mv_id}/archive",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Archived"


# ── Delete ──────────────────────────────────────────────────────


def test_delete_training_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    resp = client.delete(
        f"/api/v1/models/{mv_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204


def test_cannot_delete_published_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv_id}/publish", headers=auth_header(token))
    resp = client.delete(
        f"/api/v1/models/{mv_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Immutability ────────────────────────────────────────────────


def test_cannot_modify_published_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv_id}/publish", headers=auth_header(token))
    # Try to mark-ready again on published model
    resp = client.patch(
        f"/api/v1/models/{mv_id}/mark-ready",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_cannot_modify_archived_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    dataset = _create_ready_dataset(client, token, floor["id"])
    create_resp = client.post(
        "/api/v1/models",
        json={
            "dataset_id": dataset["id"],
            "floor_id": floor["id"],
            "algorithm": "knn",
        },
        headers=auth_header(token),
    )
    mv_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv_id}/archive", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/models/{mv_id}/mark-ready",
        headers=auth_header(token),
    )
    assert resp.status_code == 409
