"""Integration tests for /videos/<path:filepath>."""
from __future__ import annotations

from pathlib import Path

import pytest
from werkzeug.exceptions import NotFound


def _write_video(base_path: str, relative_path: str, content: bytes) -> Path:
    file_path = Path(base_path) / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    return file_path


def test_serve_video_from_storage_root(client, tmp_video_storage_config):
    """Файл из корня storage отдается по /videos/<file>."""
    _write_video(
        tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        "root-video.mp4",
        b"root-video",
    )

    response = client.get("/videos/root-video.mp4")

    assert response.status_code == 200
    assert response.data == b"root-video"


def test_serve_video_from_signs_subdirectory(client, tmp_video_storage_config):
    """Файл из подпапки signs/... отдается корректно."""
    _write_video(
        tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        "signs/greetings/hello.mp4",
        b"sign-video",
    )

    response = client.get("/videos/signs/greetings/hello.mp4")

    assert response.status_code == 200
    assert response.data == b"sign-video"


def test_serve_video_from_lessons_subdirectory(client, tmp_video_storage_config):
    """Файл из подпапки lessons/... отдается корректно."""
    _write_video(
        tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        "lessons/lesson-1.mp4",
        b"lesson-video",
    )

    response = client.get("/videos/lessons/lesson-1.mp4")

    assert response.status_code == 200
    assert response.data == b"lesson-video"


def test_serve_video_blocks_path_traversal(client, tmp_path, tmp_video_storage_config):
    """Traversal через ../ не должен выходить за пределы storage."""
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    response = client.get("/videos/../secret.txt")

    assert response.status_code == 404


def test_serve_video_blocks_urlencoded_path_traversal(client, tmp_path, tmp_video_storage_config):
    """Traversal в URL-encoded виде тоже должен давать 404."""
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    response = client.get("/videos/%2e%2e/secret.txt")

    assert response.status_code == 404


def test_serve_video_returns_404_for_missing_file(client):
    """Несуществующий путь возвращает 404."""
    response = client.get("/videos/missing-file.mp4")

    assert response.status_code == 404


def test_serve_video_handles_invalid_filepath_value(app):
    """Невалидное значение filepath не ломает handler и приводит к 404."""
    with app.test_request_context("/videos/invalid"):
        with pytest.raises(NotFound):
            app.view_functions["serve_video"](None)
