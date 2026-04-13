"""Smoke checks for shared test infrastructure."""
from pathlib import Path

import bcrypt


def test_sqlite_app_fixture_uses_tmp_video_storage(app_sqlite, tmp_video_storage_config):
    """SQLite app поднимается с тестовым local storage."""
    assert app_sqlite.config["TESTING"] is True
    assert app_sqlite.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")
    assert app_sqlite.config["VIDEO_STORAGE_TYPE"] == "local"
    assert app_sqlite.config["VIDEO_STORAGE_PATH"] == tmp_video_storage_config["VIDEO_STORAGE_PATH"]
    assert app_sqlite.config["VIDEO_BASE_URL"] == tmp_video_storage_config["VIDEO_BASE_URL"]
    assert Path(tmp_video_storage_config["VIDEO_STORAGE_PATH"]).exists()


def test_admin_auth_fixtures_create_real_bcrypt_user(admin_user, auth_headers):
    """Фикстуры создают валидного админа и Bearer headers."""
    assert admin_user.username == "testadmin"
    assert bcrypt.checkpw(b"testpass", admin_user.password_hash.encode("utf-8"))
    assert auth_headers["Authorization"].startswith("Bearer ")
