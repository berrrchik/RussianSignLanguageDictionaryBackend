"""Integration tests for admin categories API."""
from __future__ import annotations

from datetime import datetime

from app.models.category import Category
from app.models.sync_metadata import SyncMetadata


def _set_old_sync_metadata(sync_metadata_factory):
    return sync_metadata_factory(last_updated=datetime(2025, 1, 1, 0, 0, 0)).last_updated


def _current_sync_updated_at():
    metadata = SyncMetadata.query.first()
    assert metadata is not None
    return metadata.last_updated


def test_list_and_get_categories(client, auth_headers, category_factory):
    category_factory(category_id="cat-a", name="А", order=2)
    category_factory(category_id="cat-b", name="Б", order=1)

    list_response = client.get("/api/v1/admin/categories", headers=auth_headers)
    get_response = client.get("/api/v1/admin/categories/cat-a", headers=auth_headers)

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.get_json()["data"]] == ["cat-b", "cat-a"]
    assert get_response.status_code == 200
    assert get_response.get_json()["data"]["id"] == "cat-a"


def test_create_category_persists_and_updates_sync_metadata(
    client, auth_headers, sync_metadata_factory
):
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.post(
        "/api/v1/admin/categories",
        headers=auth_headers,
        json={"id": "cat-a", "name": "Алфавит", "order": 1},
    )

    assert response.status_code == 201
    assert Category.query.get("cat-a") is not None
    assert _current_sync_updated_at() > previous_sync


def test_create_category_rejects_duplicate_id(client, auth_headers, category_factory):
    category_factory(category_id="cat-a", name="А", order=1)

    response = client.post(
        "/api/v1/admin/categories",
        headers=auth_headers,
        json={"id": "cat-a", "name": "Дубль", "order": 2},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "DUPLICATE_ID"


def test_update_category_updates_entity_and_sync_metadata(
    client, auth_headers, category_factory, sync_metadata_factory
):
    category_factory(category_id="cat-a", name="А", order=1)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.put(
        "/api/v1/admin/categories/cat-a",
        headers=auth_headers,
        json={"name": "Обновлённая", "order": 5},
    )

    assert response.status_code == 200
    refreshed = Category.query.get("cat-a")
    assert refreshed.name == "Обновлённая"
    assert refreshed.order == 5
    assert _current_sync_updated_at() > previous_sync


def test_delete_category_with_signs_returns_400(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")

    response = client.delete("/api/v1/admin/categories/cat-a", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "CATEGORY_HAS_SIGNS"


def test_delete_empty_category_updates_sync_metadata(
    client, auth_headers, category_factory, sync_metadata_factory
):
    category_factory(category_id="cat-a", name="А", order=1)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.delete("/api/v1/admin/categories/cat-a", headers=auth_headers)

    assert response.status_code == 200
    assert Category.query.get("cat-a") is None
    assert _current_sync_updated_at() > previous_sync


def test_category_signs_returns_sorted_signs(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="beta", category_id="cat-a")
    sign_factory(sign_id="sign-2", word="ёж", category_id="cat-a")
    sign_factory(sign_id="sign-3", word="арбуз", category_id="cat-a")

    response = client.get("/api/v1/admin/categories/cat-a/signs", headers=auth_headers)

    assert response.status_code == 200
    assert [item["word"] for item in response.get_json()["data"]] == ["арбуз", "ёж", "beta"]
