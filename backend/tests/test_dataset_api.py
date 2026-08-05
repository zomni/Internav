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


def _create_completed_campaign(client: TestClient, token: str, floor_id: str, cell_ids: list[str] | None = None) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/campaigns",
        json={"name": "Completed Campaign"},
        headers=auth_header(token),
    )
    campaign = resp.json()["data"]
    cid = campaign["id"]
    client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    client.patch(
        f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token)
    )
    if cell_ids:
        for cell_id in cell_ids:
            _add_fingerprint(client, token, cid, cell_id)
    client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))
    return client.get(f"/api/v1/campaigns/{cid}", headers=auth_header(token)).json()["data"]


def _create_collecting_campaign(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/campaigns",
        json={"name": "Collecting Campaign"},
        headers=auth_header(token),
    )
    campaign = resp.json()["data"]
    cid = campaign["id"]
    client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    client.patch(
        f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token)
    )
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


# ── Dataset Create & List ───────────────────────────────────────


def test_create_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "My Dataset"
    assert data["status"] == "Draft"


def test_list_datasets(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    client.post(
        "/api/v1/datasets",
        json={"name": "Dataset 1"},
        headers=auth_header(token),
    )
    client.post(
        "/api/v1/datasets",
        json={"name": "Dataset 2"},
        headers=auth_header(token),
    )
    resp = client.get("/api/v1/datasets", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2


def test_get_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = create_resp.json()["data"]["id"]
    resp = client.get(f"/api/v1/datasets/{ds_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == ds_id


def test_get_dataset_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/datasets/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


# ── Dataset Add Campaigns ───────────────────────────────────────


def test_add_campaigns_to_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["fingerprint_count"] == 1
    assert resp.json()["data"]["floor_count"] == 1


def test_add_non_completed_campaign_rejected(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_collecting_campaign(client, token, floor["id"])
    _add_fingerprint(client, token, campaign["id"], cell["id"])

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_add_duplicate_campaign_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Dataset Build ───────────────────────────────────────────────


def test_build_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/build",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Ready"


def test_build_empty_dataset_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "Empty Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/build",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Dataset Archive & Delete ────────────────────────────────────


def test_archive_ready_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    client.patch(f"/api/v1/datasets/{ds_id}/build", headers=auth_header(token))

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/archive",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Archived"


def test_delete_draft_dataset(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    resp = client.delete(f"/api/v1/datasets/{ds_id}", headers=auth_header(token))
    assert resp.status_code == 204


def test_delete_ready_dataset_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    campaign = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [campaign["id"]]},
        headers=auth_header(token),
    )
    client.patch(f"/api/v1/datasets/{ds_id}/build", headers=auth_header(token))

    resp = client.delete(f"/api/v1/datasets/{ds_id}", headers=auth_header(token))
    assert resp.status_code == 409


def test_add_campaigns_to_immutable_dataset_rejected(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid = _create_grid(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    c1 = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )
    c2 = _create_completed_campaign(
        client, token, floor["id"], cell_ids=[cell["id"]]
    )

    ds_resp = client.post(
        "/api/v1/datasets",
        json={"name": "My Dataset"},
        headers=auth_header(token),
    )
    ds_id = ds_resp.json()["data"]["id"]

    client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [c1["id"]]},
        headers=auth_header(token),
    )
    client.patch(f"/api/v1/datasets/{ds_id}/build", headers=auth_header(token))

    resp = client.patch(
        f"/api/v1/datasets/{ds_id}/add-campaigns",
        json={"campaign_ids": [c2["id"]]},
        headers=auth_header(token),
    )
    assert resp.status_code == 409
