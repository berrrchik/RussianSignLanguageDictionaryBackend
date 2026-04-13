"""Unit tests for Flask decorators."""
from __future__ import annotations

from unittest import mock

from flask import jsonify

from app.database import db
from app.utils.decorators import handle_db_errors, require_json


def test_require_json_allows_valid_json(app):
    @require_json
    def view():
        return jsonify({"ok": True}), 200

    with app.test_request_context(json={"value": 1}):
        response, status_code = view()

    assert status_code == 200
    assert response.get_json() == {"ok": True}


def test_require_json_rejects_empty_json_body(app):
    @require_json
    def view():
        return jsonify({"ok": True}), 200

    with app.test_request_context(json={}):
        response, status_code = view()

    assert status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_REQUEST"


def test_handle_db_errors_rolls_back_and_returns_internal_error(app):
    @handle_db_errors("создания сущности")
    def failing_view():
        raise RuntimeError("db exploded")

    with app.app_context():
        with app.test_request_context():
            with mock.patch.object(db.session, "rollback") as rollback_spy:
                with mock.patch.object(app.logger, "error") as logger_spy:
                    response, status_code = failing_view()

    assert rollback_spy.call_count == 1
    assert status_code == 500
    assert response.get_json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.get_json()["error"]["message"] == "Ошибка создания сущности"
    assert "создания сущности" in logger_spy.call_args.args[0]


def test_handle_db_errors_uses_operation_name_in_logs(app):
    @handle_db_errors("обновления жеста")
    def failing_view():
        raise ValueError("boom")

    with app.app_context():
        with app.test_request_context():
            with mock.patch.object(db.session, "rollback"):
                with mock.patch.object(app.logger, "error") as logger_spy:
                    failing_view()

    assert logger_spy.call_count == 1
    assert logger_spy.call_args.kwargs["extra"]["extra_data"]["operation"] == "обновления жеста"
