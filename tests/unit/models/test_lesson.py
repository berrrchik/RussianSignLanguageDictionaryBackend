"""Тесты сериализации Lesson."""
from __future__ import annotations

from datetime import datetime

from app.models.lesson import Lesson


def test_lesson_to_dict_uses_unix_timestamps():
    lesson = Lesson(
        id="lesson_1",
        title="Урок 1",
        description="Описание",
        video_url="lessons/lesson-1.mp4",
        order=1,
        created_at=datetime(2026, 4, 13, 10, 30, 0),
        updated_at=datetime(2026, 4, 13, 11, 45, 30),
    )

    payload = lesson.to_dict()

    assert payload["created_at"] == 1776076200
    assert payload["updated_at"] == 1776080730


def test_lesson_to_dict_with_timestamps_matches_to_dict():
    lesson = Lesson(
        id="lesson_1",
        title="Урок 1",
        description="Описание",
        video_url="lessons/lesson-1.mp4",
        order=1,
        created_at=datetime(2026, 4, 13, 10, 30, 0),
        updated_at=datetime(2026, 4, 13, 11, 45, 30),
    )

    assert lesson.to_dict_with_timestamps() == lesson.to_dict()
