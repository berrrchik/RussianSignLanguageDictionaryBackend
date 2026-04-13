"""Unit tests for API response helpers."""
from __future__ import annotations

from flask import Flask

from app.utils.responses import (
    error_response,
    internal_error_response,
    not_found_response,
    success_response,
    validation_error_response,
)


def test_success_response_builds_expected_body():
    app = Flask(__name__)

    with app.app_context():
        response, status_code = success_response(
            data={"id": 1},
            message="ok",
            status_code=201,
        )

    assert status_code == 201
    assert response.get_json() == {
        "success": True,
        "data": {"id": 1},
        "message": "ok",
    }


def test_error_response_builds_expected_structure():
    app = Flask(__name__)

    with app.app_context():
        response, status_code = error_response(
            "NOT_FOUND",
            "Ресурс не найден",
            404,
        )

    assert status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "Ресурс не найден",
        },
    }


def test_validation_error_response_joins_multiple_errors():
    app = Flask(__name__)

    with app.app_context():
        response, status_code = validation_error_response(
            ["Поле name обязательно", "Поле order должно быть числом"]
        )

    assert status_code == 400
    assert response.get_json()["error"]["message"] == (
        "Поле name обязательно; Поле order должно быть числом"
    )


def test_not_found_and_internal_error_responses_return_expected_codes():
    app = Flask(__name__)

    with app.app_context():
        not_found, not_found_status = not_found_response("Категория")
        internal_error, internal_status = internal_error_response()

    assert not_found_status == 404
    assert not_found.get_json()["error"]["message"] == "Категория не найден"
    assert internal_status == 500
    assert internal_error.get_json()["error"]["code"] == "INTERNAL_ERROR"
