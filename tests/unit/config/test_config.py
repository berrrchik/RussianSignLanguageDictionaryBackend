"""Тесты для app.config."""
from __future__ import annotations

from flask import Flask

from app.config import Config


def test_init_app_creates_local_video_storage_directory(tmp_path):
    """Config.init_app создаёт директорию local storage."""
    storage_path = tmp_path / "nested" / "videos"
    app = Flask(__name__)
    app.config["VIDEO_STORAGE_TYPE"] = "local"
    app.config["VIDEO_STORAGE_PATH"] = str(storage_path)

    Config.init_app(app)

    assert storage_path.exists()
    assert storage_path.is_dir()
