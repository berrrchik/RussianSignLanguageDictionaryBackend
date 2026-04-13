"""Unit tests for local video storage."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from flask import Flask
from werkzeug.datastructures import FileStorage

from app.utils.storage import LocalVideoStorage, get_video_storage


def test_local_video_storage_upload_saves_file_and_returns_relative_path(tmp_path):
    storage = LocalVideoStorage(
        storage_path=str(tmp_path / "videos"),
        base_url="http://testserver.local/videos",
    )
    file_obj = FileStorage(stream=BytesIO(b"video-bytes"), filename="demo.mp4")

    file_path, url = storage.upload(file_obj, sign_id="sign_1", filename="demo.mp4", category_id="cat_1")

    assert file_path == "signs/cat_1/sign_1_demo.mp4"
    assert url == "http://testserver.local/videos/signs/cat_1/sign_1_demo.mp4"
    assert (tmp_path / "videos" / file_path).read_bytes() == b"video-bytes"


def test_local_video_storage_get_url_builds_url_for_relative_path(tmp_path):
    storage = LocalVideoStorage(
        storage_path=str(tmp_path / "videos"),
        base_url="http://testserver.local/videos",
    )

    assert storage.get_url("signs/cat_1/sign_1_demo.mp4") == (
        "http://testserver.local/videos/signs/cat_1/sign_1_demo.mp4"
    )


def test_local_video_storage_get_url_normalizes_absolute_path_inside_storage(tmp_path):
    storage_root = tmp_path / "videos"
    storage = LocalVideoStorage(
        storage_path=str(storage_root),
        base_url="http://testserver.local/videos",
    )
    absolute_path = storage_root / "signs" / "cat_1" / "sign_1_demo.mp4"

    assert storage.get_url(str(absolute_path)) == (
        "http://testserver.local/videos/signs/cat_1/sign_1_demo.mp4"
    )


def test_local_video_storage_delete_removes_existing_file(tmp_path):
    storage_root = tmp_path / "videos"
    storage = LocalVideoStorage(
        storage_path=str(storage_root),
        base_url="http://testserver.local/videos",
    )
    target = storage_root / "signs" / "cat_1" / "sign_1_demo.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"video-bytes")

    deleted = storage.delete("signs/cat_1/sign_1_demo.mp4")

    assert deleted is True
    assert not target.exists()


def test_local_video_storage_delete_returns_false_for_missing_file(tmp_path):
    storage = LocalVideoStorage(
        storage_path=str(tmp_path / "videos"),
        base_url="http://testserver.local/videos",
    )

    assert storage.delete("signs/cat_1/missing.mp4") is False


def test_get_video_storage_returns_local_backend_from_app_config(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config["VIDEO_STORAGE_PATH"] = str(tmp_path / "videos")
    app.config["VIDEO_BASE_URL"] = "http://testserver.local/videos"
    monkeypatch.setenv("VIDEO_STORAGE_TYPE", "local")

    with app.app_context():
        storage = get_video_storage()

    assert isinstance(storage, LocalVideoStorage)
    assert storage.storage_path == Path(app.config["VIDEO_STORAGE_PATH"])
