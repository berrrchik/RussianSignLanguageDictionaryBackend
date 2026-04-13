"""Integration tests for admin lessons API."""
from __future__ import annotations

import builtins
from datetime import datetime
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app.models.lesson import Lesson
from app.models.sync_metadata import SyncMetadata


def _set_old_sync_metadata(sync_metadata_factory):
    return sync_metadata_factory(last_updated=datetime(2025, 1, 1, 0, 0, 0)).last_updated


def _current_sync_updated_at():
    metadata = SyncMetadata.query.first()
    assert metadata is not None
    return metadata.last_updated


def _lesson_file_path(app, lesson_id: str) -> Path:
    filename = lesson_id.replace("_", "-") + ".mp4"
    return Path(app.config["VIDEO_STORAGE_PATH"]) / "lessons" / filename


def test_list_get_create_update_delete_lesson_with_sync_metadata(
    client, auth_headers, lesson_factory, sync_metadata_factory
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание 1",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )

    list_response = client.get("/api/v1/admin/lessons", headers=auth_headers)
    get_response = client.get("/api/v1/admin/lessons/lesson_1", headers=auth_headers)

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.get_json()["data"]] == ["lesson_1"]
    assert get_response.status_code == 200
    assert get_response.get_json()["data"]["title"] == "Первый урок"

    previous_sync = _set_old_sync_metadata(sync_metadata_factory)
    create_response = client.post(
        "/api/v1/admin/lessons",
        headers=auth_headers,
        json={
            "id": "lesson_2",
            "title": "Новый урок",
            "description": "Описание 2",
            "video_url": "/lessons/lesson-2.mp4",
            "order": 2,
        },
    )
    assert create_response.status_code == 201
    assert Lesson.query.get("lesson_2") is not None
    assert _current_sync_updated_at() > previous_sync

    previous_sync = _set_old_sync_metadata(sync_metadata_factory)
    update_response = client.put(
        "/api/v1/admin/lessons/lesson_2",
        headers=auth_headers,
        json={
            "title": "Обновлённый урок",
            "description": "Описание 2+",
            "video_url": "/lessons/lesson-2-updated.mp4",
            "order": 3,
        },
    )
    assert update_response.status_code == 200
    assert Lesson.query.get("lesson_2").title == "Обновлённый урок"
    assert _current_sync_updated_at() > previous_sync

    previous_sync = _set_old_sync_metadata(sync_metadata_factory)
    delete_response = client.delete("/api/v1/admin/lessons/lesson_2", headers=auth_headers)
    assert delete_response.status_code == 200
    assert Lesson.query.get("lesson_2") is None
    assert _current_sync_updated_at() > previous_sync


def test_create_lesson_rejects_invalid_payload(client, auth_headers):
    response = client.post(
        "/api/v1/admin/lessons",
        headers=auth_headers,
        json={"title": "Урок", "description": "Описание", "order": 1},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_lesson_accepts_string_order_from_swagger(
    client, auth_headers, lesson_factory, sync_metadata_factory
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.put(
        "/api/v1/admin/lessons/lesson_1",
        headers=auth_headers,
        json={
            "title": "Первый урок",
            "description": "Описание",
            "video_url": "/lessons/lesson-1.mp4",
            "order": "7",
        },
    )

    assert response.status_code == 200
    assert Lesson.query.get("lesson_1").order == 7
    assert _current_sync_updated_at() > previous_sync


def test_update_lesson_rejects_non_numeric_order(client, auth_headers, lesson_factory):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )

    response = client.put(
        "/api/v1/admin/lessons/lesson_1",
        headers=auth_headers,
        json={
            "title": "Первый урок",
            "description": "Описание",
            "video_url": "/lessons/lesson-1.mp4",
            "order": "wrong",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_lesson_removes_local_file_if_present(
    client, auth_headers, lesson_factory, sync_metadata_factory, app
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )
    file_path = _lesson_file_path(app, "lesson_1")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"video")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.delete("/api/v1/admin/lessons/lesson_1", headers=auth_headers)

    assert response.status_code == 200
    assert Lesson.query.get("lesson_1") is None
    assert not file_path.exists()
    assert _current_sync_updated_at() > previous_sync


def test_delete_lesson_does_not_fail_when_local_unlink_raises(
    client, auth_headers, lesson_factory, sync_metadata_factory, app, monkeypatch
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )
    file_path = _lesson_file_path(app, "lesson_1")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"video")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)
    original_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if self == file_path:
            raise OSError("cannot unlink")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    response = client.delete("/api/v1/admin/lessons/lesson_1", headers=auth_headers)

    assert response.status_code == 200
    assert Lesson.query.get("lesson_1") is None
    assert _current_sync_updated_at() > previous_sync


def test_delete_lesson_video_rejects_empty_video_url(client, auth_headers, lesson_factory):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )

    response = client.delete("/api/v1/admin/lessons/lesson_1/video", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "У урока нет видео для удаления"


def test_upload_lesson_video_requires_file(client, auth_headers, lesson_factory):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )

    response = client.post("/api/v1/admin/lessons/lesson_1/video", headers=auth_headers)

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "NO_FILE"


def test_upload_lesson_video_rejects_empty_filename(client, auth_headers, lesson_factory):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "NO_FILE"


def test_upload_lesson_video_rejects_invalid_extension(client, auth_headers, lesson_factory):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.avi")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_FILE"


def test_upload_lesson_video_rejects_too_large_file(client, auth_headers, lesson_factory, monkeypatch):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )
    monkeypatch.setattr(
        FileStorage,
        "content_length",
        property(lambda self: 50 * 1024 * 1024 + 1),
    )

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_lesson_video_local_saves_file_and_updates_sync_metadata(
    client, auth_headers, lesson_factory, sync_metadata_factory, app
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["video_url"] == "/lessons/lesson-1.mp4"
    assert Lesson.query.get("lesson_1").video_url == "/lessons/lesson-1.mp4"
    assert _lesson_file_path(app, "lesson_1").exists()
    assert _current_sync_updated_at() > previous_sync


def test_delete_lesson_video_local_clears_url_and_updates_sync_metadata(
    client, auth_headers, lesson_factory, sync_metadata_factory, app
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="/lessons/lesson-1.mp4",
        order=1,
    )
    file_path = _lesson_file_path(app, "lesson_1")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"video")
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.delete("/api/v1/admin/lessons/lesson_1/video", headers=auth_headers)

    assert response.status_code == 200
    assert Lesson.query.get("lesson_1").video_url == ""
    assert not file_path.exists()
    assert _current_sync_updated_at() > previous_sync


def test_upload_lesson_video_returns_config_error_for_supabase_without_env(
    client, auth_headers, lesson_factory, monkeypatch
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )
    monkeypatch.setenv("VIDEO_STORAGE_TYPE", "supabase")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "CONFIG_ERROR"


def test_upload_lesson_video_returns_dependency_error_when_supabase_missing(
    client, auth_headers, lesson_factory, monkeypatch
):
    lesson_factory(
        lesson_id="lesson_1",
        title="Первый урок",
        description="Описание",
        video_url="",
        order=1,
    )
    monkeypatch.setenv("VIDEO_STORAGE_TYPE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "supabase":
            raise ImportError("missing supabase")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    response = client.post(
        "/api/v1/admin/lessons/lesson_1/video",
        headers=auth_headers,
        data={"file": (BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "DEPENDENCY_ERROR"
