from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin


def test_list_users(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get("/api/v1/users", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


def test_get_user(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get("/api/v1/users", headers=auth_header(token))
    user_id = resp.json()["data"][0]["id"]
    resp = client.get(f"/api/v1/users/{user_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == user_id


def test_create_user(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/users",
        json={
            "email": "operator@test.com",
            "password": "Operator123!",
            "role": "Operator",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["email"] == "operator@test.com"
    assert data["role"] == "Operator"


def test_create_duplicate_user_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    client.post(
        "/api/v1/users",
        json={
            "email": "dup@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    resp = client.post(
        "/api/v1/users",
        json={
            "email": "dup@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_update_role(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/users",
        json={
            "email": "role@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    user_id = create_resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "Operator"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "Operator"


def test_update_password(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/users",
        json={
            "email": "pwd@test.com",
            "password": "OldPass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    user_id = create_resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}/password",
        json={"new_password": "NewPass456!"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == user_id


def test_deactivate_user(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/users",
        json={
            "email": "deact@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    user_id = create_resp.json()["data"]["id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}/deactivate",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False


def test_activate_user(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/users",
        json={
            "email": "act@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    user_id = create_resp.json()["data"]["id"]
    client.patch(f"/api/v1/users/{user_id}/deactivate", headers=auth_header(token))
    resp = client.patch(
        f"/api/v1/users/{user_id}/activate",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True


def test_delete_user(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    create_resp = client.post(
        "/api/v1/users",
        json={
            "email": "del@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    user_id = create_resp.json()["data"]["id"]
    resp = client.delete(
        f"/api/v1/users/{user_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 204


def test_cannot_delete_administrator(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get("/api/v1/users", headers=auth_header(token))
    admin_id = resp.json()["data"][0]["id"]
    resp = client.delete(
        f"/api/v1/users/{admin_id}",
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_requires_admin_role(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    # Create a Viewer user
    client.post(
        "/api/v1/users",
        json={
            "email": "viewer@test.com",
            "password": "Pass123!",
            "role": "Viewer",
        },
        headers=auth_header(token),
    )
    viewer_email = "viewer@test.com"
    viewer_password = "Pass123!"
    # Login as viewer
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": viewer_email, "password": viewer_password},
    )
    viewer_token = login_resp.json()["data"]["access_token"]
    resp = client.get("/api/v1/users", headers=auth_header(viewer_token))
    assert resp.status_code == 403
