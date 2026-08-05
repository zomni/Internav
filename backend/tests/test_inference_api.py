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


def _setup_floor_with_published_model(client: TestClient, token: str) -> dict:
    floor = _setup_floor(client, token)
    fid = floor["id"]

    # Create campaign
    resp = client.post(
        f"/api/v1/floors/{fid}/campaigns",
        json={"name": "Campaign"},
        headers=auth_header(token),
    )
    campaign = resp.json()["data"]
    cid = campaign["id"]

    # Start + collecting
    client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    client.patch(f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token))

    # Grid + cell + fingerprint
    grid = _create_grid(client, token, fid)
    cell = _get_walkable_cell(client, token, grid["id"])
    _add_fingerprint(client, token, cid, cell["id"])

    # Complete campaign
    client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))

    # Dataset
    resp = client.post(
        "/api/v1/datasets",
        json={"name": "DS"},
        headers=auth_header(token),
    )
    dsid = resp.json()["data"]["id"]
    client.patch(
        f"/api/v1/datasets/{dsid}/add-campaigns",
        json={"campaign_ids": [cid]},
        headers=auth_header(token),
    )
    client.patch(f"/api/v1/datasets/{dsid}/build", headers=auth_header(token))

    # Model
    resp = client.post(
        "/api/v1/models",
        json={"dataset_id": dsid, "floor_id": fid, "algorithm": "knn"},
        headers=auth_header(token),
    )
    mv_id = resp.json()["data"]["id"]
    client.patch(f"/api/v1/models/{mv_id}/mark-ready", headers=auth_header(token))
    client.patch(f"/api/v1/models/{mv_id}/publish", headers=auth_header(token))

    return {"floor": floor, "cell": cell, "grid": grid, "campaign": campaign}


# ── Inference Tests ─────────────────────────────────────────────


def test_estimate_position(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    result = _setup_floor_with_published_model(client, token)
    resp = client.post(
        "/api/v1/inference",
        json={
            "floor_id": result["floor"]["id"],
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
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["predicted_cell_id"] == result["cell"]["id"]
    assert data["confidence"] > 0
    assert data["model_version_id"] != ""
    assert len(data["candidate_cells"]) >= 1


def test_estimate_position_no_model(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        "/api/v1/inference",
        json={
            "floor_id": floor["id"],
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
    assert resp.status_code == 404


def test_estimate_position_no_observations(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        "/api/v1/inference",
        json={
            "floor_id": floor["id"],
            "observations": [],
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


def test_estimate_position_no_match(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    result = _setup_floor_with_published_model(client, token)
    resp = client.post(
        "/api/v1/inference",
        json={
            "floor_id": result["floor"]["id"],
            "observations": [
                {
                    "bssid": "FF:FF:FF:FF:FF:FF",
                    "ssid": "Unknown-WiFi",
                    "rssi": -80,
                    "frequency": 5180,
                }
            ],
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_estimate_position_requires_auth(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/inference",
        json={
            "floor_id": "00000000-0000-0000-0000-000000000000",
            "observations": [],
        },
    )
    assert resp.status_code in (401, 403)
