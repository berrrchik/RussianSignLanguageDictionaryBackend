"""Тесты Pydantic raw response models."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.models.responses import (
    CategoryRawResponse,
    LessonRawResponse,
    SignRawResponse,
    SignVideoRawResponse,
    SyncDataRawResponse,
    SyncMetadataRawResponse,
)


def test_sign_video_raw_response_serializes_timestamps():
    model = SignVideoRawResponse(
        id=1,
        url="http://example.com/video.mp4",
        context_description="Основное видео",
        order=0,
        created_at=datetime(2026, 4, 13, 8, 0, 0),
        updated_at=datetime(2026, 4, 13, 9, 30, 0),
    )

    payload = model.model_dump(mode="json")

    assert payload["created_at"] == 1776067200
    assert payload["updated_at"] == 1776072600


def test_sign_raw_response_accepts_orm_like_data():
    orm_like_sign = SimpleNamespace(
        id="sign_1",
        word="привет",
        description=None,
        category_id="cat_1",
        videos=[
            SimpleNamespace(
                id=1,
                url="http://example.com/video.mp4",
                context_description="Основное видео",
                order=0,
                created_at=datetime(2026, 4, 13, 8, 0, 0),
                updated_at=datetime(2026, 4, 13, 9, 0, 0),
            )
        ],
        synonyms=[SimpleNamespace(id="sign_2", word="здравствуй")],
        created_at=datetime(2026, 4, 13, 10, 0, 0),
        updated_at=datetime(2026, 4, 13, 11, 0, 0),
    )

    model = SignRawResponse.model_validate(orm_like_sign, from_attributes=True)
    payload = model.model_dump(mode="json")

    assert payload["description"] is None
    assert payload["videos"][0]["created_at"] == 1776067200
    assert payload["synonyms"] == [{"id": "sign_2", "word": "здравствуй"}]
    assert payload["created_at"] == 1776074400
    assert payload["updated_at"] == 1776078000


def test_other_raw_responses_serialize_timestamps_correctly():
    category = CategoryRawResponse(
        id="cat_1",
        name="Категория",
        order=1,
        sign_count=0,
        created_at=datetime(2026, 4, 13, 7, 0, 0),
        updated_at=datetime(2026, 4, 13, 8, 0, 0),
    )
    lesson = LessonRawResponse(
        id="lesson_1",
        title="Урок 1",
        description="Описание",
        video_url="lessons/lesson-1.mp4",
        order=1,
        created_at=datetime(2026, 4, 13, 12, 0, 0),
        updated_at=datetime(2026, 4, 13, 13, 0, 0),
    )
    sync_metadata = SyncMetadataRawResponse(
        last_updated=datetime(2026, 4, 13, 14, 0, 0),
        has_updates=True,
    )
    sync_data = SyncDataRawResponse(
        categories=[category],
        signs=[],
        lessons=[lesson],
        last_updated=datetime(2026, 4, 13, 15, 0, 0),
    )

    assert category.model_dump(mode="json")["created_at"] == 1776063600
    assert lesson.model_dump(mode="json")["updated_at"] == 1776085200
    assert sync_metadata.model_dump(mode="json")["last_updated"] == 1776088800
    assert sync_data.model_dump(mode="json")["last_updated"] == 1776092400


def test_raw_response_optional_fields_are_accepted():
    orm_like_sign = SimpleNamespace(
        id="sign_1",
        word="привет",
        description=None,
        category_id="cat_1",
        videos=[],
        synonyms=[],
        created_at=datetime(2026, 4, 13, 10, 0, 0),
        updated_at=datetime(2026, 4, 13, 11, 0, 0),
    )

    payload = SignRawResponse.model_validate(orm_like_sign, from_attributes=True).model_dump(mode="json")

    assert payload["description"] is None
    assert payload["videos"] == []
    assert payload["synonyms"] == []
