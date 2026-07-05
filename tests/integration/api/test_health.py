"""Integration tests for health check endpoints."""
from __future__ import annotations

from app import create_app


def test_health_returns_ok_payload(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": "1.0.0"}


def test_api_health_alias_returns_ok_payload(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": "1.0.0"}


def test_version_comes_from_app_config(test_config_factory, tmp_video_storage_config):
    test_config = test_config_factory(
        database_uri="sqlite://",
        video_storage_path=tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        video_base_url=tmp_video_storage_config["VIDEO_BASE_URL"],
        config_overrides={"APP_VERSION": "2.3.4"},
    )
    app = create_app(test_config)

    response = app.test_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "version": "2.3.4"}
