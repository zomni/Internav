from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin

SVG_PLAN = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="3000">'
    b'<rect width="2000" height="3000" fill="white"/>'
    b'<path d="M400 400H1600V2600H400V400Z" stroke="black"/>'
    b"</svg>"
)


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
    floor = _create_floor(client, token, building["id"])
    return floor


def _upload(client: TestClient, token: str, floor_id: str, content: bytes = SVG_PLAN):
    return client.post(
        f"/api/v1/floors/{floor_id}/floor-plans",
        files={"file": ("plan.svg", content, "image/svg+xml")},
        headers=auth_header(token),
    )


# ── FloorPlan Upload ──────────────────────────────────────────


def test_upload_floor_plan(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = _upload(client, token, floor["id"])
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["floor_id"] == floor["id"]
    assert data["width"] == 2000
    assert data["height"] == 3000
    assert data["mime_type"] == "image/svg+xml"
    assert data["version"] == 1
    assert data["is_active"] is True


def test_upload_floor_plan_requires_file(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(f"/api/v1/floors/{floor['id']}/floor-plans", headers=auth_header(token))
    assert resp.status_code == 422


def test_upload_floor_plan_non_svg_requires_dimensions(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/floor-plans",
        files={"file": ("plan.png", b"not-a-real-png", "image/png")},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "width and height" in resp.json()["detail"]


def test_list_floor_plans(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload(client, token, floor["id"])
    resp = client.get(f"/api/v1/floors/{floor['id']}/floor-plans", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_get_floor_plan(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    upload_resp = _upload(client, token, floor["id"])
    fp_id = upload_resp.json()["data"]["id"]
    resp = client.get(f"/api/v1/floor-plans/{fp_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == fp_id


def test_get_floor_plan_image(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    upload_resp = _upload(client, token, floor["id"])
    fp_id = upload_resp.json()["data"]["id"]
    resp = client.get(f"/api/v1/floor-plans/{fp_id}/image", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.content == SVG_PLAN
    assert resp.headers["content-type"].startswith("image/svg+xml")


def test_get_floor_plan_image_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/floor-plans/00000000-0000-0000-0000-000000000000/image",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_get_floor_plan_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/floor-plans/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_floor_plan_versioning(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    r1 = _upload(client, token, floor["id"], content=b'<svg width="10" height="10"><rect width="10" height="10" fill="white"/></svg>')
    assert r1.json()["data"]["version"] == 1
    assert r1.json()["data"]["is_active"] is True

    r2 = _upload(client, token, floor["id"], content=b'<svg width="20" height="20"><rect width="20" height="20" fill="white"/></svg>')
    assert r2.json()["data"]["version"] == 2
    assert r2.json()["data"]["is_active"] is True

    list_resp = client.get(f"/api/v1/floors/{floor['id']}/floor-plans", headers=auth_header(token))
    items = list_resp.json()["data"]
    assert len(items) == 2
    old = next(i for i in items if i["version"] == 1)
    assert old["is_active"] is False


def test_upload_floor_plan_missing_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/floors/00000000-0000-0000-0000-000000000000/floor-plans",
        files={"file": ("plan.svg", SVG_PLAN, "image/svg+xml")},
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_delete_floor_plan_requires_inactive(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    r = _upload(client, token, floor["id"])
    fp_id = r.json()["data"]["id"]
    resp = client.delete(f"/api/v1/floor-plans/{fp_id}", headers=auth_header(token))
    assert resp.status_code == 409


def test_delete_floor_plan(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload(client, token, floor["id"])
    _upload(client, token, floor["id"])
    inactive_id = None
    list_resp = client.get(f"/api/v1/floors/{floor['id']}/floor-plans", headers=auth_header(token))
    for item in list_resp.json()["data"]:
        if item["version"] == 1:
            inactive_id = item["id"]
    assert inactive_id is not None
    resp = client.delete(f"/api/v1/floor-plans/{inactive_id}", headers=auth_header(token))
    assert resp.status_code == 204
