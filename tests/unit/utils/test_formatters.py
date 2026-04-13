"""Unit tests for datetime formatters."""
from __future__ import annotations

from datetime import datetime, timezone

from app.utils.formatters import format_datetime


def test_format_datetime_adds_z_suffix():
    dt = datetime(2026, 4, 13, 12, 30, 45, 123456)

    assert format_datetime(dt) == "2026-04-13T12:30:45.123456Z"


def test_format_datetime_handles_aware_datetime_stably():
    dt = datetime(2026, 4, 13, 12, 30, 45, tzinfo=timezone.utc)

    assert format_datetime(dt) == "2026-04-13T12:30:45Z"


def test_format_datetime_returns_none_for_none():
    assert format_datetime(None) is None
