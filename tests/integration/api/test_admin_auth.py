"""Integration tests for admin authentication API."""
from __future__ import annotations

from app.models.admin_user import AdminUser


def test_admin_login_returns_token_and_expires_in(client, admin_user):
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": admin_user.username, "password": "testpass"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["data"]["token"], str)
    assert payload["data"]["token"]
    assert payload["data"]["expires_in"] == 3600


def test_admin_login_requires_username_and_password(client):
    response = client.post("/api/v1/admin/auth/login", json={"username": "testadmin"})

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "MISSING_CREDENTIALS",
        "message": "Требуются username и password",
    }


def test_admin_login_rejects_empty_json_via_require_json(client):
    response = client.post("/api/v1/admin/auth/login", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "INVALID_REQUEST",
        "message": "Требуется JSON тело запроса",
    }


def test_admin_login_rejects_invalid_password(client, admin_user):
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": admin_user.username, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == {
        "code": "INVALID_CREDENTIALS",
        "message": "Неверный username или password",
    }


def test_admin_login_updates_last_login(app, client, admin_user):
    assert admin_user.last_login is None

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": admin_user.username, "password": "testpass"},
    )

    assert response.status_code == 200

    with app.app_context():
        refreshed_user = AdminUser.query.get(admin_user.id)

    assert refreshed_user is not None
    assert refreshed_user.last_login is not None
