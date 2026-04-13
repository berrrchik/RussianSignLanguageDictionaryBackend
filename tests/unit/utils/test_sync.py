"""Unit tests for sync metadata helpers."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.models.sync_metadata import SyncMetadata
from app.utils import sync as sync_utils


def test_get_or_create_sync_metadata_creates_record_when_missing(app_ctx):
    metadata = sync_utils.get_or_create_sync_metadata()

    assert metadata.id is not None
    assert SyncMetadata.query.count() == 1


def test_update_sync_metadata_updates_existing_record(app_ctx, monkeypatch):
    metadata = SyncMetadata(last_updated=datetime(2026, 1, 1, 12, 0, 0))
    from app.database import db

    db.session.add(metadata)
    db.session.commit()
    fresh_dt = datetime(2026, 1, 2, 12, 0, 0)
    monkeypatch.setattr(sync_utils, "datetime", SimpleNamespace(utcnow=lambda: fresh_dt))

    sync_utils.update_sync_metadata()

    assert SyncMetadata.query.first().last_updated == fresh_dt


def test_update_sync_metadata_creates_record_when_missing(app_ctx, monkeypatch):
    fresh_dt = datetime(2026, 1, 3, 12, 0, 0)
    monkeypatch.setattr(sync_utils, "datetime", SimpleNamespace(utcnow=lambda: fresh_dt))

    sync_utils.update_sync_metadata()

    metadata = SyncMetadata.query.first()
    assert metadata is not None
    assert metadata.last_updated == fresh_dt
