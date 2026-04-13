"""Integration tests for critical raw sync endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from app.database import db
from app.models.sign_synonym import SignSynonym
from app.models.sync_metadata import SyncMetadata
from app.utils.serializers import serialize_datetime


def _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory):
    category_factory(category_id="cat-1", name="База", order=1)

    sign_factory(
        sign_id="sign-main",
        word="арбуз",
        category_id="cat-1",
        description="Есть видео и синонимы",
        created_at=datetime(2025, 1, 15, 10, 0, 0),
        updated_at=datetime(2025, 1, 15, 10, 5, 0),
    )
    sign_video_factory(
        sign_id="sign-main",
        video_id=1,
        file_path="signs/base/main.mp4",
        context_description="Основной ракурс",
        order=0,
        created_at=datetime(2025, 1, 15, 10, 10, 0),
        updated_at=datetime(2025, 1, 15, 10, 15, 0),
    )

    sign_factory(
        sign_id="sign-empty-video",
        word="яблоко",
        category_id="cat-1",
        created_at=datetime(2025, 1, 15, 9, 0, 0),
        updated_at=datetime(2025, 1, 15, 9, 5, 0),
    )
    sign_factory(
        sign_id="sign-synonym",
        word="ёж",
        category_id="cat-1",
        created_at=datetime(2025, 1, 15, 8, 0, 0),
        updated_at=datetime(2025, 1, 15, 8, 5, 0),
    )
    sign_factory(
        sign_id="sign-latin",
        word="beta",
        category_id="cat-1",
        created_at=datetime(2025, 1, 15, 7, 0, 0),
        updated_at=datetime(2025, 1, 15, 7, 5, 0),
    )
    sign_factory(
        sign_id="sign-symbol",
        word="1жест",
        category_id="cat-1",
        created_at=datetime(2025, 1, 15, 6, 0, 0),
        updated_at=datetime(2025, 1, 15, 6, 5, 0),
    )

    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-main", sign_id_2="sign-synonym"),
            SignSynonym(sign_id_1="sign-synonym", sign_id_2="sign-main"),
        ]
    )

    lesson_factory(
        lesson_id="lesson-supabase",
        title="Урок из Supabase",
        description="Видео пришло из public bucket",
        video_url=(
            "https://project.supabase.co/storage/v1/object/public/"
            "lessons/lesson-supabase.mp4"
        ),
        order=1,
        created_at=datetime(2025, 1, 15, 11, 0, 0),
        updated_at=datetime(2025, 1, 15, 11, 5, 0),
    )
    lesson_factory(
        lesson_id="lesson-local",
        title="Локальный урок",
        description="Путь уже локальный",
        video_url="/lessons/already-local.mp4",
        order=2,
        created_at=datetime(2025, 1, 15, 12, 0, 0),
        updated_at=datetime(2025, 1, 15, 12, 5, 0),
    )

    db.session.commit()


class TestSyncCheckRaw:
    def test_returns_raw_payload_and_creates_metadata_when_missing(self, app, client):
        with app.app_context():
            assert SyncMetadata.query.count() == 0

        response = client.get("/api/v1/sync/check/raw")

        assert response.status_code == 200
        assert "ETag" in response.headers
        payload = response.get_json()
        assert "success" not in payload
        assert "data" not in payload
        assert set(payload) == {"last_updated", "has_updates"}
        assert isinstance(payload["last_updated"], int)
        assert payload["has_updates"] is True

        with app.app_context():
            assert SyncMetadata.query.count() == 1

    def test_returns_304_on_full_etag_match(self, client, sync_metadata_factory):
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 10, 30, 0))

        first_response = client.get("/api/v1/sync/check/raw")
        etag = first_response.headers["ETag"]

        second_response = client.get(
            "/api/v1/sync/check/raw",
            headers={"If-None-Match": etag},
        )

        assert second_response.status_code == 304
        assert second_response.get_data(as_text=True) == ""

    def test_partial_if_none_match_does_not_return_304(self, client, sync_metadata_factory):
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 10, 30, 0))

        first_response = client.get("/api/v1/sync/check/raw")
        partial_etag = first_response.headers["ETag"].strip('"')[:10]

        second_response = client.get(
            "/api/v1/sync/check/raw",
            headers={"If-None-Match": partial_etag},
        )

        assert second_response.status_code == 200
        assert second_response.get_json()["has_updates"] is True

    def test_invalid_timestamp_returns_400(self, client, sync_metadata_factory):
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 10, 30, 0))

        response = client.get("/api/v1/sync/check/raw?last_updated=not-a-timestamp")

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "ValidationError",
            "message": "Invalid timestamp format: not-a-timestamp",
        }

    def test_has_updates_is_false_for_newer_client_timestamp(self, client, sync_metadata_factory):
        server_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        sync_metadata_factory(last_updated=server_dt)

        response = client.get(
            f"/api/v1/sync/check/raw?last_updated={serialize_datetime(server_dt)}"
        )

        assert response.status_code == 200
        assert response.get_json()["has_updates"] is False

    def test_has_updates_is_true_for_older_client_timestamp(self, client, sync_metadata_factory):
        server_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        sync_metadata_factory(last_updated=server_dt)
        client_dt = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

        response = client.get(
            f"/api/v1/sync/check/raw?last_updated={serialize_datetime(client_dt)}"
        )

        assert response.status_code == 200
        assert response.get_json()["has_updates"] is True


class TestSyncDataRaw:
    def test_returns_raw_sync_payload_with_unix_timestamps(
        self,
        client,
        category_factory,
        sign_factory,
        sign_video_factory,
        lesson_factory,
        sync_metadata_factory,
    ):
        metadata_dt = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory)
        sync_metadata_factory(last_updated=metadata_dt)

        response = client.get("/api/v1/sync/data/raw")

        assert response.status_code == 200
        payload = response.get_json()
        assert "success" not in payload
        assert "data" not in payload
        assert set(payload) == {"categories", "signs", "lessons", "last_updated"}
        assert payload["last_updated"] == serialize_datetime(metadata_dt)

        category_payload = payload["categories"][0]
        assert isinstance(category_payload["created_at"], int)
        assert isinstance(category_payload["updated_at"], int)

        sign_payload = next(item for item in payload["signs"] if item["id"] == "sign-main")
        assert isinstance(sign_payload["created_at"], int)
        assert isinstance(sign_payload["updated_at"], int)
        assert isinstance(sign_payload["videos"][0]["created_at"], int)
        assert isinstance(sign_payload["videos"][0]["updated_at"], int)

        lesson_payload = next(item for item in payload["lessons"] if item["id"] == "lesson-supabase")
        assert isinstance(lesson_payload["created_at"], int)
        assert isinstance(lesson_payload["updated_at"], int)

    def test_sign_without_video_does_not_break_response(
        self,
        client,
        category_factory,
        sign_factory,
        sign_video_factory,
        lesson_factory,
        sync_metadata_factory,
    ):
        _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory)
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 13, 0, 0))

        response = client.get("/api/v1/sync/data/raw")

        assert response.status_code == 200
        payload = response.get_json()
        empty_video_sign = next(
            item for item in payload["signs"] if item["id"] == "sign-empty-video"
        )
        assert empty_video_sign["videos"] == []

    def test_deduplicates_bidirectional_synonyms(
        self,
        client,
        category_factory,
        sign_factory,
        sign_video_factory,
        lesson_factory,
        sync_metadata_factory,
    ):
        _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory)
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 13, 0, 0))

        response = client.get("/api/v1/sync/data/raw")

        assert response.status_code == 200
        sign_payload = next(
            item for item in response.get_json()["signs"] if item["id"] == "sign-main"
        )
        assert sign_payload["synonyms"] == [{"id": "sign-synonym", "word": "ёж"}]

    def test_converts_supabase_and_local_lesson_paths(
        self,
        client,
        category_factory,
        sign_factory,
        sign_video_factory,
        lesson_factory,
        sync_metadata_factory,
    ):
        _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory)
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 13, 0, 0))

        response = client.get("/api/v1/sync/data/raw")

        assert response.status_code == 200
        lessons_by_id = {
            lesson["id"]: lesson for lesson in response.get_json()["lessons"]
        }
        assert lessons_by_id["lesson-supabase"]["video_url"] == "/lessons/lesson-supabase.mp4"
        assert lessons_by_id["lesson-local"]["video_url"] == "/lessons/already-local.mp4"

    def test_sorts_signs_using_russian_sorting(
        self,
        client,
        category_factory,
        sign_factory,
        sign_video_factory,
        lesson_factory,
        sync_metadata_factory,
    ):
        _seed_sync_dataset(category_factory, sign_factory, sign_video_factory, lesson_factory)
        sync_metadata_factory(last_updated=datetime(2025, 1, 15, 13, 0, 0))

        response = client.get("/api/v1/sync/data/raw")

        assert response.status_code == 200
        words = [item["word"] for item in response.get_json()["signs"]]
        assert words == ["арбуз", "ёж", "яблоко", "beta", "1жест"]
