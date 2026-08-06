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
    fp = _create_floor_plan(client, token, floor_id)
    resp = client.post(
        f"/api/v1/floors/{floor_id}/grids",
        json={"name": "Main Grid", "cell_size": 3},
        headers=auth_header(token),
    )
    return resp.json()["data"], fp


def _create_campaign(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/campaigns",
        json={"name": "Test Campaign"},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _start_campaign_collecting(client: TestClient, token: str, campaign_id: str) -> None:
    client.patch(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_header(token))
    client.patch(
        f"/api/v1/campaigns/{campaign_id}/begin-collecting",
        headers=auth_header(token),
    )


def _get_walkable_cell(client: TestClient, token: str, grid_id: str) -> dict:
    resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    for cell in resp.json()["data"]:
        if cell["walkable"]:
            return cell
    raise AssertionError("No walkable cell found")


# ── Fingerprint Create ─────────────────────────────────────────


def test_create_fingerprint_with_observations(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    resp = client.post(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        json={
            "cell_id": cell["id"],
            "device_id": "DEVICE-001",
            "captured_at": "2026-07-27T12:00:00Z",
            "sample_number": 1,
            "orientation": 90.0,
            "observations": [
                {
                    "bssid": "AA:BB:CC:DD:EE:01",
                    "ssid": "WiFi-1",
                    "rssi": -45,
                    "frequency": 2412,
                    "channel": 1,
                    "band": "2.4GHz",
                    "security": "WPA2",
                },
                {
                    "bssid": "AA:BB:CC:DD:EE:02",
                    "ssid": "WiFi-2",
                    "rssi": -72,
                    "frequency": 5180,
                    "channel": 36,
                    "band": "5GHz",
                    "security": "WPA3",
                },
            ],
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["device_id"] == "DEVICE-001"
    assert data["sample_number"] == 1
    assert data["orientation"] == 90.0
    assert len(data["observations"]) == 2


def test_create_fingerprint_no_observations_rejected(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    resp = client.post(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        json={
            "cell_id": cell["id"],
            "device_id": "DEVICE-001",
            "captured_at": "2026-07-27T12:00:00Z",
            "sample_number": 1,
            "observations": [],
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


def test_create_fingerprint_no_campaign_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    resp = client.post(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        json={
            "cell_id": cell["id"],
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
    assert resp.status_code == 409


# ── Fingerprint Read ────────────────────────────────────────────


def test_get_fingerprint_with_observations(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    create_resp = client.post(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        json={
            "cell_id": cell["id"],
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
    fp_id = create_resp.json()["data"]["id"]

    resp = client.get(f"/api/v1/fingerprints/{fp_id}", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["device_id"] == "DEVICE-001"
    assert len(data["observations"]) == 1
    assert data["observations"][0]["bssid"] == "AA:BB:CC:DD:EE:01"


def test_list_fingerprints_by_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    for i in range(3):
        client.post(
            f"/api/v1/campaigns/{campaign['id']}/fingerprints",
            json={
                "cell_id": cell["id"],
                "device_id": f"DEVICE-{i:03d}",
                "captured_at": f"2026-07-27T12:00:{i:02d}Z",
                "sample_number": i,
                "observations": [
                    {
                        "bssid": f"AA:BB:CC:DD:EE:{i:02d}",
                        "ssid": f"WiFi-{i}",
                        "rssi": -50 - i * 10,
                        "frequency": 2412,
                    }
                ],
            },
            headers=auth_header(token),
        )

    resp = client.get(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 3


def test_count_fingerprints_by_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    for i in range(2):
        client.post(
            f"/api/v1/campaigns/{campaign['id']}/fingerprints",
            json={
                "cell_id": cell["id"],
                "device_id": f"DEVICE-{i:03d}",
                "captured_at": f"2026-07-27T12:00:{i:02d}Z",
                "sample_number": i,
                "observations": [
                    {
                        "bssid": f"AA:BB:CC:DD:EE:{i:02d}",
                        "ssid": f"WiFi-{i}",
                        "rssi": -50,
                        "frequency": 2412,
                    }
                ],
            },
            headers=auth_header(token),
        )

    resp = client.get(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints/count",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["campaign_id"] == campaign["id"]
    assert data["count"] == 2


def test_count_fingerprints_campaign_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/campaigns/00000000-0000-0000-0000-000000000000/fingerprints/count",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def _create_fingerprint(
    client: TestClient, token: str, campaign_id: str, cell_id: str, device_id: str = "DEVICE-001"
) -> dict:
    resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/fingerprints",
        json={
            "cell_id": cell_id,
            "device_id": device_id,
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
    assert resp.status_code == 201
    return resp.json()["data"]


# ── Fingerprint Delete ──────────────────────────────────────────


def test_delete_fingerprint_active_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])
    fp = _create_fingerprint(client, token, campaign["id"], cell["id"])

    resp = client.delete(f"/api/v1/fingerprints/{fp['id']}", headers=auth_header(token))
    assert resp.status_code == 204

    listed = client.get(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        headers=auth_header(token),
    )
    assert listed.status_code == 200
    assert listed.json()["data"] == []


def test_delete_fingerprint_completed_campaign_rejected(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])
    fp = _create_fingerprint(client, token, campaign["id"], cell["id"])

    client.patch(f"/api/v1/campaigns/{campaign['id']}/complete", headers=auth_header(token))

    resp = client.delete(f"/api/v1/fingerprints/{fp['id']}", headers=auth_header(token))
    assert resp.status_code == 409

    listed = client.get(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        headers=auth_header(token),
    )
    assert len(listed.json()["data"]) == 1


def test_delete_fingerprint_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.delete(
        "/api/v1/fingerprints/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_delete_fingerprint_requires_operator(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    client.post(
        "/api/v1/users",
        json={
            "email": "viewer@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@test.com", "password": "Pass123!"},
    )
    viewer_token = login_resp.json()["data"]["access_token"]

    resp = client.delete(
        "/api/v1/fingerprints/00000000-0000-0000-0000-000000000000",
        headers=auth_header(viewer_token),
    )
    assert resp.status_code == 403


# ── Fingerprint Immutability ────────────────────────────────────


def test_fingerprint_immutable_after_creation(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    grid, _ = _create_grid(client, token, floor["id"])
    campaign = _create_campaign(client, token, floor["id"])
    _start_campaign_collecting(client, token, campaign["id"])
    cell = _get_walkable_cell(client, token, grid["id"])

    create_resp = client.post(
        f"/api/v1/campaigns/{campaign['id']}/fingerprints",
        json={
            "cell_id": cell["id"],
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
    assert create_resp.status_code == 201

    from datetime import UTC, datetime
    from uuid import uuid4

    from app.domain.entities.fingerprint import Fingerprint

    fp = Fingerprint(
        campaign_id=uuid4(),
        cell_id=uuid4(),
        device_id="test",
        captured_at=datetime.now(UTC),
        sample_number=1,
    )
    fp.ensure_immutable()

    import pytest

    from app.domain.errors import BusinessRuleViolation

    fp2 = Fingerprint(
        campaign_id=uuid4(),
        cell_id=uuid4(),
        device_id="test",
        captured_at=datetime.now(UTC),
        sample_number=1,
    )
    fp2.touch()
    with pytest.raises(BusinessRuleViolation):
        fp2.ensure_immutable()
