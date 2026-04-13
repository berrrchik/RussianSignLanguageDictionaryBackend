"""Тесты для bootstrap фабрики Flask-приложения."""
from __future__ import annotations

import builtins
import logging
from unittest import mock

from app import create_app
from app.database import db
from app.utils import logging_config


def _build_test_app(test_config_factory, tmp_video_storage_config):
    test_config = test_config_factory(
        database_uri="sqlite://",
        video_storage_path=tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        video_base_url=tmp_video_storage_config["VIDEO_BASE_URL"],
    )
    app = create_app(test_config)
    with app.app_context():
        db.create_all()
    return app


def _restore_root_logger():
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    return root_logger, original_handlers, original_level


def _reset_root_logger(root_logger, original_handlers, original_level):
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_create_app_registers_expected_blueprints(
    test_config_factory,
    tmp_video_storage_config,
):
    """Фабрика регистрирует API и web blueprints."""
    root_logger, original_handlers, original_level = _restore_root_logger()
    try:
        app = _build_test_app(test_config_factory, tmp_video_storage_config)
    finally:
        _reset_root_logger(root_logger, original_handlers, original_level)

    assert {"sync", "search", "admin", "admin_pages"} <= set(app.blueprints)


def test_create_app_enables_extensions_cors_and_swagger(
    test_config_factory,
    tmp_video_storage_config,
):
    """Фабрика подключает Compress, CORS и Swagger UI route."""
    root_logger, original_handlers, original_level = _restore_root_logger()
    try:
        app = _build_test_app(test_config_factory, tmp_video_storage_config)
        client = app.test_client()
        response = client.get(
            "/api/v1/sync/check/raw",
            headers={"Origin": "http://example.com"},
        )
    finally:
        _reset_root_logger(root_logger, original_handlers, original_level)

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "compress" in app.extensions
    assert any(rule.startswith("/api-docs") for rule in rules)
    assert response.headers.get("Access-Control-Allow-Origin") in {"*", "http://example.com"}


def test_create_app_does_not_fail_without_prometheus_exporter(
    monkeypatch,
    test_config_factory,
    tmp_video_storage_config,
):
    """Отсутствие prometheus_flask_exporter не ломает startup."""
    original_import = builtins.__import__
    root_logger, original_handlers, original_level = _restore_root_logger()

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "prometheus_flask_exporter":
            raise ImportError("prometheus unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        app = _build_test_app(test_config_factory, tmp_video_storage_config)
    finally:
        _reset_root_logger(root_logger, original_handlers, original_level)

    assert app is not None
    assert "sync" in app.blueprints


def test_create_app_registers_logging_hooks(
    test_config_factory,
    tmp_video_storage_config,
):
    """Фабрика подключает before/after hooks из log_request()."""
    captured_hooks = {}
    root_logger, original_handlers, original_level = _restore_root_logger()

    def fake_log_request():
        before_request, after_request = logging_config.log_request()
        captured_hooks["before"] = before_request
        captured_hooks["after"] = after_request
        return before_request, after_request

    try:
        with mock.patch("app.utils.logging_config.log_request", side_effect=fake_log_request) as log_request_spy:
            with mock.patch("app.utils.logging_config.setup_logging", wraps=logging_config.setup_logging) as setup_logging_spy:
                app = _build_test_app(test_config_factory, tmp_video_storage_config)
    finally:
        _reset_root_logger(root_logger, original_handlers, original_level)

    assert setup_logging_spy.call_count == 1
    assert log_request_spy.call_count == 1
    assert captured_hooks["before"] in app.before_request_funcs[None]
    assert captured_hooks["after"] in app.after_request_funcs[None]
