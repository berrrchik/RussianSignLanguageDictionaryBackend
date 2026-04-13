"""Integration tests for admin videos API."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest import mock

from app.constants import VIDEO_MAX_SIZE
from app.models.sign_video import SignVideo
from app.models.sync_metadata import SyncMetadata


def _seed_sign(category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    return sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")


def _set_old_sync_metadata(sync_metadata_factory):
    return sync_metadata_factory(last_updated=datetime(2025, 1, 1, 0, 0, 0)).last_updated


def _current_sync_updated_at():
    metadata = SyncMetadata.query.first()
    assert metadata is not None
    return metadata.last_updated


def test_list_videos_by_sign(client, auth_headers, category_factory, sign_factory, sign_video_factory, app):
    _seed_sign(category_factory, sign_factory)
    sign_video_factory(sign_id="sign-1", video_id=2, file_path="signs/cat-a/two.mp4", order=1)
    sign_video_factory(sign_id="sign-1", video_id=1, file_path="signs/cat-a/one.mp4", order=0)

    response = client.get("/api/v1/admin/signs/sign-1/videos", headers=auth_headers)

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert [item["id"] for item in payload] == [1, 2]
    assert payload[0]["url"] == f'{app.config["VIDEO_BASE_URL"]}/signs/cat-a/one.mp4'


def test_upload_video_requires_file(client, auth_headers, category_factory, sign_factory):
    _seed_sign(category_factory, sign_factory)

    response = client.post("/api/v1/admin/signs/sign-1/videos", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "NO_FILE"


def test_upload_video_rejects_empty_filename(client, auth_headers, category_factory, sign_factory):
    _seed_sign(category_factory, sign_factory)

    response = client.post(
        "/api/v1/admin/signs/sign-1/videos",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), ""), "context_description": "main"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "NO_FILE"


def test_upload_video_rejects_non_mp4_extension(client, auth_headers, category_factory, sign_factory):
    _seed_sign(category_factory, sign_factory)

    response = client.post(
        "/api/v1/admin/signs/sign-1/videos",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.avi"), "context_description": "main"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_video_rejects_file_larger_than_50mb(client, auth_headers, category_factory, sign_factory):
    _seed_sign(category_factory, sign_factory)

    response = client.post(
        "/api/v1/admin/signs/sign-1/videos",
        headers=auth_headers,
        data={
            "file": (BytesIO(b"x" * (VIDEO_MAX_SIZE + 1)), "clip.mp4"),
            "context_description": "main",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_video_coerces_non_numeric_order_to_zero_and_updates_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sync_metadata_factory, app
):
    _seed_sign(category_factory, sign_factory)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.post(
        "/api/v1/admin/signs/sign-1/videos",
        headers=auth_headers,
        data={
            "file": (BytesIO(b"video-bytes"), "clip.mp4"),
            "context_description": "main",
            "order": "not-a-number",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()["data"]
    assert payload["order"] == 0
    created = SignVideo.query.get(payload["id"])
    assert created is not None
    assert created.file_path == "signs/cat-a/sign-1_clip.mp4"
    assert Path(app.config["VIDEO_STORAGE_PATH"], created.file_path).exists()
    assert _current_sync_updated_at() > previous_sync


def test_upload_video_returns_500_when_storage_raises(
    client, auth_headers, category_factory, sign_factory, monkeypatch
):
    _seed_sign(category_factory, sign_factory)
    storage = mock.Mock()
    storage.upload.side_effect = RuntimeError("storage exploded")
    monkeypatch.setattr("app.routes.admin.videos.get_video_storage", lambda: storage)

    response = client.post(
        "/api/v1/admin/signs/sign-1/videos",
        headers=auth_headers,
        data={
            "file": (BytesIO(b"video-bytes"), "clip.mp4"),
            "context_description": "main",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "INTERNAL_ERROR"


def test_update_video_accepts_string_order_and_updates_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sign_video_factory, sync_metadata_factory
):
    _seed_sign(category_factory, sign_factory)
    sign_video_factory(sign_id="sign-1", video_id=1, file_path="signs/cat-a/one.mp4", order=0)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.put(
        "/api/v1/admin/videos/1",
        headers=auth_headers,
        json={"context_description": "updated", "order": "7"},
    )

    assert response.status_code == 200
    refreshed = SignVideo.query.get(1)
    assert refreshed.context_description == "updated"
    assert refreshed.order == 7
    assert _current_sync_updated_at() > previous_sync


def test_update_video_rejects_non_numeric_order(client, auth_headers, category_factory, sign_factory, sign_video_factory):
    _seed_sign(category_factory, sign_factory)
    sign_video_factory(sign_id="sign-1", video_id=1, file_path="signs/cat-a/one.mp4", order=0)

    response = client.put(
        "/api/v1/admin/videos/1",
        headers=auth_headers,
        json={"order": "wrong"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "Поле order должно быть целым числом"


def test_delete_video_removes_record_and_updates_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sign_video_factory, sync_metadata_factory, app
):
    _seed_sign(category_factory, sign_factory)
    sign_video_factory(sign_id="sign-1", video_id=1, file_path="signs/cat-a/one.mp4", order=0)
    Path(app.config["VIDEO_STORAGE_PATH"], "signs/cat-a").mkdir(parents=True, exist_ok=True)
    Path(app.config["VIDEO_STORAGE_PATH"], "signs/cat-a/one.mp4").write_bytes(b"video")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.delete("/api/v1/admin/videos/1", headers=auth_headers)

    assert response.status_code == 200
    assert SignVideo.query.get(1) is None
    assert not Path(app.config["VIDEO_STORAGE_PATH"], "signs/cat-a/one.mp4").exists()
    assert _current_sync_updated_at() > previous_sync
