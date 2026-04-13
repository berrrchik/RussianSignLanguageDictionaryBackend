"""Unit tests for timestamp serializers."""
from __future__ import annotations

from datetime import datetime, timezone

from app.utils.serializers import deserialize_datetime, serialize_datetime


def test_serialize_datetime_returns_integer_timestamp():
    dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    assert serialize_datetime(dt) == 1736937000


def test_serialize_datetime_treats_naive_datetime_as_utc():
    naive_dt = datetime(2025, 1, 15, 10, 30, 0)
    aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    assert serialize_datetime(naive_dt) == serialize_datetime(aware_dt)


def test_deserialize_datetime_returns_utc_datetime():
    restored = deserialize_datetime(1736937000)

    assert restored == datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_serialize_deserialize_roundtrip_preserves_seconds():
    original = datetime(2026, 4, 13, 14, 22, 11, tzinfo=timezone.utc)

    restored = deserialize_datetime(serialize_datetime(original))

    assert restored.year == original.year
    assert restored.month == original.month
    assert restored.day == original.day
    assert restored.hour == original.hour
    assert restored.minute == original.minute
    assert restored.second == original.second


def test_serialize_and_deserialize_return_none_for_none():
    assert serialize_datetime(None) is None
    assert deserialize_datetime(None) is None
