"""Unit tests for ETag helpers."""
from __future__ import annotations

from flask import Flask

from app.utils.etag import (
    check_etag_match,
    create_response_with_etag,
    generate_etag,
    normalize_etag,
)


def test_generate_etag_is_deterministic_for_same_json_payload():
    left = {"b": 2, "a": 1, "nested": {"x": 1}}
    right = {"nested": {"x": 1}, "a": 1, "b": 2}

    assert generate_etag(left) == generate_etag(right)


def test_normalize_etag_removes_double_quotes():
    assert normalize_etag('"abc123"') == "abc123"


def test_normalize_etag_removes_single_quotes():
    assert normalize_etag("'abc123'") == "abc123"


def test_normalize_etag_removes_gzip_suffix():
    assert normalize_etag('"abcdef1234567890abcdef1234567890:gzip"') == "abcdef1234567890abcdef1234567890"


def test_normalize_etag_keeps_short_hash_as_is():
    assert normalize_etag('"shortetag:gzip"') == "shortetag"


def test_normalize_etag_trims_main_part_longer_than_32_chars():
    long_main = "a" * 40

    assert normalize_etag(f'"{long_main}:gzip"') == "a" * 32


def test_check_etag_match_returns_304_only_for_full_match():
    app = Flask(__name__)
    computed = generate_etag({"value": 1})

    with app.test_request_context(headers={"If-None-Match": f'"{computed}"'}):
        response = check_etag_match(computed, "/sync/data/raw")

    assert response is not None
    assert response.status_code == 304


def test_check_etag_match_does_not_return_304_for_partial_match():
    app = Flask(__name__)
    computed = generate_etag({"value": 1})
    partial = computed[:16]

    with app.test_request_context(headers={"If-None-Match": f'"{partial}"'}):
        response = check_etag_match(computed, "/sync/data/raw")

    assert response is None


def test_create_response_with_etag_sets_quoted_header():
    app = Flask(__name__)
    payload = {"value": 1}
    expected_etag = generate_etag(payload)

    with app.app_context():
        with app.test_request_context():
            response, status_code = create_response_with_etag(payload, "/sync/data/raw")

    assert status_code == 200
    assert response.headers["ETag"] == f'"{expected_etag}"'
    assert response.get_json() == payload
