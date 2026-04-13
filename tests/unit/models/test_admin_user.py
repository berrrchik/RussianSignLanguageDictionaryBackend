"""Тесты сериализации AdminUser."""
from __future__ import annotations

from datetime import datetime

from app.models.admin_user import AdminUser


def test_admin_user_to_dict_excludes_password_hash():
    admin = AdminUser(
        id=1,
        username="admin",
        password_hash="super-secret-hash",
        created_at=datetime(2026, 4, 13, 9, 0, 0),
        last_login=datetime(2026, 4, 13, 10, 0, 0),
    )

    payload = admin.to_dict()

    assert payload == {
        "id": 1,
        "username": "admin",
        "created_at": "2026-04-13T09:00:00Z",
        "last_login": "2026-04-13T10:00:00Z",
    }
    assert "password_hash" not in payload


def test_admin_user_to_dict_handles_empty_last_login():
    admin = AdminUser(
        id=1,
        username="admin",
        password_hash="super-secret-hash",
        created_at=datetime(2026, 4, 13, 9, 0, 0),
        last_login=None,
    )

    payload = admin.to_dict()

    assert payload["last_login"] is None
