"""Unit tests for JWT auth helpers."""
from __future__ import annotations

import jwt
import pytest
from flask import g, jsonify, request

from app.database import db
from app.models.admin_user import AdminUser
from app.utils.auth import generate_token, require_auth, verify_token


def test_generate_token_and_verify_token_form_valid_pair(app_sqlite):
    token = generate_token(42, app_sqlite.config["JWT_SECRET_KEY"], 3600)

    payload = verify_token(token, app_sqlite.config["JWT_SECRET_KEY"])

    assert payload["user_id"] == 42


def test_verify_token_rejects_invalid_token(app_sqlite):
    with pytest.raises(jwt.InvalidTokenError):
        verify_token("not-a-jwt", app_sqlite.config["JWT_SECRET_KEY"])


def test_require_auth_rejects_missing_header(app, client):
    @app.route("/test-auth/missing")
    @require_auth
    def protected_view():
        return jsonify({"ok": True})

    response = client.get("/test-auth/missing")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "TOKEN_REQUIRED"


def test_require_auth_rejects_malformed_bearer_header(app, client):
    @app.route("/test-auth/malformed")
    @require_auth
    def protected_view():
        return jsonify({"ok": True})

    response = client.get("/test-auth/malformed", headers={"Authorization": "Bearer"})

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "INVALID_TOKEN_FORMAT"


def test_require_auth_rejects_expired_token(app, client, admin_user):
    expired_token = generate_token(
        admin_user.id,
        app.config["JWT_SECRET_KEY"],
        -1,
    )

    @app.route("/test-auth/expired")
    @require_auth
    def protected_view():
        return jsonify({"ok": True})

    response = client.get(
        "/test-auth/expired",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "TOKEN_EXPIRED"


def test_require_auth_rejects_deleted_user_after_token_issue(app, client, admin_user):
    token = generate_token(
        admin_user.id,
        app.config["JWT_SECRET_KEY"],
        3600,
    )
    db.session.delete(admin_user)
    db.session.commit()

    @app.route("/test-auth/deleted-user")
    @require_auth
    def protected_view():
        return jsonify({"ok": True})

    response = client.get(
        "/test-auth/deleted-user",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "USER_NOT_FOUND"


def test_require_auth_populates_request_and_g_context(app, client, admin_user):
    token = generate_token(
        admin_user.id,
        app.config["JWT_SECRET_KEY"],
        3600,
    )

    @app.route("/test-auth/context")
    @require_auth
    def protected_view():
        return jsonify(
            {
                "user_id": g.user_id,
                "username": g.username,
                "current_user": request.current_user.username,
            }
        )

    response = client.get(
        "/test-auth/context",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "user_id": admin_user.id,
        "username": admin_user.username,
        "current_user": admin_user.username,
    }
