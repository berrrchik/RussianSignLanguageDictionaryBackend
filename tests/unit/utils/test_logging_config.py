"""Тесты для structured logging config."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from unittest import mock

import pytest
from flask import Flask

from app.utils.logging_config import (
    JSONFormatter,
    _derive_event_domain,
    _status_family,
    setup_logging,
)


@pytest.fixture
def restore_root_logger():
    """Возвращает root logger в исходное состояние после теста."""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    yield root_logger

    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


def test_json_formatter_includes_base_fields():
    """JSONFormatter добавляет базовые структурные поля."""
    logger = logging.getLogger("tests.logging")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=21,
        msg="bootstrap ready",
        args=(),
        exc_info=None,
        extra={
            "event_kind": "request",
            "event_domain": "sync",
        },
    )

    payload = json.loads(JSONFormatter().format(record))

    assert payload["timestamp"]
    assert payload["level"] == "INFO"
    assert payload["message"] == "bootstrap ready"
    assert payload["module"] == "test_logging_config"
    assert payload["event_kind"] == "request"
    assert payload["event_domain"] == "sync"


def test_json_formatter_flattens_extra_data_and_serializes_datetime():
    """JSONFormatter переносит extra_data и безопасно сериализует datetime."""
    happened_at = datetime(2026, 4, 13, 12, 30, 45)
    logger = logging.getLogger("tests.logging")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=48,
        msg="business event",
        args=(),
        exc_info=None,
        extra={
            "event_kind": "business",
            "event_domain": "admin_api",
            "extra_data": {
                "happened_at": happened_at,
                "entity_id": "sign_1",
            },
        },
    )

    payload = json.loads(JSONFormatter().format(record))

    assert payload["extra"]["entity_id"] == "sign_1"
    assert payload["extra"]["happened_at"] == happened_at.isoformat()
    assert payload["entity_id"] == "sign_1"
    assert payload["happened_at"] == happened_at.isoformat()


@pytest.mark.parametrize(
    ("path", "blueprint", "expected"),
    [
        ("/api/v1/sync/check/raw", "", "sync"),
        ("/api/v1/search/sbert", "", "search"),
        ("/api/v1/admin/auth/login", "", "admin_auth"),
        ("/api/v1/admin/signs", "", "admin_api"),
        ("/admin/dashboard", "", "admin_web"),
        ("/videos/signs/demo.mp4", "", "videos"),
        ("/api-docs", "", "docs"),
        ("/apispec.json", "", "docs"),
        ("/custom", "custom_bp", "custom_bp"),
    ],
)
def test_derive_event_domain(path, blueprint, expected):
    """Функция корректно определяет event domain."""
    assert _derive_event_domain(path, blueprint) == expected


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (204, "2xx"),
        (404, "4xx"),
        (503, "5xx"),
        (None, "unknown"),
        ("oops", "unknown"),
    ],
)
def test_status_family(status_code, expected):
    """Функция возвращает корректное семейство HTTP статуса."""
    assert _status_family(status_code) == expected


def test_setup_logging_survives_file_handler_failure(monkeypatch, restore_root_logger):
    """setup_logging не падает, если FileHandler недоступен."""
    app = Flask(__name__)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_FILE", "/restricted/app.log")

    with mock.patch("logging.FileHandler", side_effect=OSError("permission denied")):
        setup_logging(app)

    handlers = logging.getLogger().handlers

    assert handlers
    assert any(isinstance(handler, logging.StreamHandler) for handler in handlers)


def test_setup_logging_keeps_console_handler_after_file_handler_failure(
    monkeypatch,
    restore_root_logger,
):
    """После ошибки файлового логгера консольный handler остаётся активным."""
    app = Flask(__name__)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_FILE", "/restricted/app.log")

    with mock.patch("logging.FileHandler", side_effect=OSError("permission denied")):
        setup_logging(app)

    handlers = logging.getLogger().handlers

    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)
    assert isinstance(handlers[0].formatter, JSONFormatter)
    assert app.logger.handlers == handlers
