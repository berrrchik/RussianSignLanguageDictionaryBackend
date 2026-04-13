"""Integration tests for admin signs API."""
from __future__ import annotations

from datetime import datetime
from unittest import mock

from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.models.sync_metadata import SyncMetadata


def _seed_signs(category_factory, sign_factory, sign_video_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    category_factory(category_id="cat-b", name="Б", order=2)

    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a", description="desc 1")
    sign_factory(sign_id="sign-2", word="ёж", category_id="cat-a", description="desc 2")
    sign_factory(sign_id="beta-sign", word="beta", category_id="cat-b", description="desc 3")
    sign_factory(sign_id="sign-3", word="яблоко", category_id="cat-a", description=None)
    sign_video_factory(
        sign_id="sign-1",
        video_id=1,
        file_path="signs/cat-a/one.mp4",
        context_description="Основной вариант",
        order=0,
    )


def _set_old_sync_metadata(sync_metadata_factory):
    return sync_metadata_factory(last_updated=datetime(2025, 1, 1, 0, 0, 0)).last_updated


def _current_sync_updated_at():
    metadata = SyncMetadata.query.first()
    assert metadata is not None
    return metadata.last_updated


def test_list_signs_supports_page_and_per_page(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")
    sign_factory(sign_id="sign-2", word="банан", category_id="cat-a")
    sign_factory(sign_id="sign-3", word="вишня", category_id="cat-a")

    response = client.get("/api/v1/admin/signs?page=2&per_page=1", headers=auth_headers)

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["pagination"] == {"page": 2, "per_page": 1, "total": 3, "pages": 3}
    assert [item["id"] for item in payload["signs"]] == ["sign-2"]


def test_list_signs_filters_by_category_id(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    category_factory(category_id="cat-b", name="Б", order=2)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")
    sign_factory(sign_id="sign-2", word="beta", category_id="cat-b")

    response = client.get("/api/v1/admin/signs?category_id=cat-a", headers=auth_headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.get_json()["data"]["signs"]] == ["sign-1"]


def test_list_signs_searches_by_word_and_id(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="target-id", word="арбуз", category_id="cat-a")
    sign_factory(sign_id="other-id", word="beta", category_id="cat-a")

    by_word = client.get("/api/v1/admin/signs?search=арб", headers=auth_headers)
    by_id = client.get("/api/v1/admin/signs?search=target", headers=auth_headers)

    assert by_word.status_code == 200
    assert [item["id"] for item in by_word.get_json()["data"]["signs"]] == ["target-id"]
    assert by_id.status_code == 200
    assert [item["id"] for item in by_id.get_json()["data"]["signs"]] == ["target-id"]


def test_list_signs_returns_empty_search_result_with_pagination(
    client, auth_headers, category_factory, sign_factory
):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")

    response = client.get("/api/v1/admin/signs?search=missing", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "signs": [],
        "pagination": {"page": 1, "per_page": 50, "total": 0, "pages": 1},
    }


def test_get_sign_by_id_returns_relations(
    client,
    auth_headers,
    category_factory,
    sign_factory,
    sign_video_factory,
    app,
):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a", description="fruit")
    sign_factory(sign_id="sign-2", word="ёж", category_id="cat-a")
    sign_video_factory(
        sign_id="sign-1",
        video_id=1,
        file_path="signs/cat-a/arbuz.mp4",
        context_description="Основное видео",
        order=0,
    )
    from app.database import db

    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-2"),
            SignSynonym(sign_id_1="sign-2", sign_id_2="sign-1"),
        ]
    )
    db.session.commit()

    response = client.get("/api/v1/admin/signs/sign-1", headers=auth_headers)

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["id"] == "sign-1"
    assert payload["videos"][0]["url"] == f'{app.config["VIDEO_BASE_URL"]}/signs/cat-a/arbuz.mp4'
    assert payload["synonyms"] == [{"id": "sign-2", "word": "ёж"}]


def test_create_sign_persists_entity_and_updates_sync_metadata(
    client, auth_headers, category_factory, sync_metadata_factory
):
    category_factory(category_id="cat-a", name="А", order=1)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.post(
        "/api/v1/admin/signs",
        headers=auth_headers,
        json={"id": "sign-new", "word": "новый", "description": "", "category_id": "cat-a"},
    )

    assert response.status_code == 201
    assert response.get_json()["data"]["id"] == "sign-new"
    assert Sign.query.get("sign-new") is not None
    assert _current_sync_updated_at() > previous_sync


def test_create_sign_rejects_duplicate_id(client, auth_headers, category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")

    response = client.post(
        "/api/v1/admin/signs",
        headers=auth_headers,
        json={"id": "sign-1", "word": "дубль", "category_id": "cat-a"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "DUPLICATE_ID"


def test_create_sign_rejects_missing_category(client, auth_headers):
    response = client.post(
        "/api/v1/admin/signs",
        headers=auth_headers,
        json={"id": "sign-1", "word": "арбуз", "category_id": "missing"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "Категория не найдена"


def test_update_sign_updates_entity_and_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sync_metadata_factory
):
    category_factory(category_id="cat-a", name="А", order=1)
    category_factory(category_id="cat-b", name="Б", order=2)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a", description="old")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.put(
        "/api/v1/admin/signs/sign-1",
        headers=auth_headers,
        json={"word": "обновлённый", "description": "new", "category_id": "cat-b"},
    )

    assert response.status_code == 200
    refreshed = Sign.query.get("sign-1")
    assert refreshed.word == "обновлённый"
    assert refreshed.description == "new"
    assert refreshed.category_id == "cat-b"
    assert _current_sync_updated_at() > previous_sync


def test_delete_sign_handles_storage_delete_false_and_updates_sync_metadata(
    client,
    auth_headers,
    category_factory,
    sign_factory,
    sign_video_factory,
    sync_metadata_factory,
    monkeypatch,
):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")
    sign_video_factory(sign_id="sign-1", video_id=1, file_path="signs/cat-a/one.mp4")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    fake_storage = mock.Mock()
    fake_storage.delete.return_value = False
    monkeypatch.setattr("app.utils.storage.get_video_storage", lambda: fake_storage)

    response = client.delete("/api/v1/admin/signs/sign-1", headers=auth_headers)

    assert response.status_code == 200
    assert Sign.query.get("sign-1") is None
    fake_storage.delete.assert_called_once_with("signs/cat-a/one.mp4")
    assert _current_sync_updated_at() > previous_sync
