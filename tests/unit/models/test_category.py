"""Тесты сериализации Category."""
from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.category import Category
from app.models.sign import Sign


class TestCategoryToDict:
    """Проверки для Category.to_dict()."""

    def test_to_dict_returns_expected_fields(self, app_ctx):
        category = Category(
            id="greetings",
            name="Приветствия",
            order=1,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 2, 13, 30, 0),
        )
        db.session.add(category)
        db.session.add(Sign(id="sign_1", word="привет", category_id="greetings"))
        db.session.commit()

        payload = category.to_dict()

        assert payload == {
            "id": "greetings",
            "name": "Приветствия",
            "order": 1,
            "sign_count": 1,
            "created_at": "2026-01-01T12:00:00Z",
            "updated_at": "2026-01-02T13:30:00Z",
        }

    def test_to_dict_returns_zero_sign_count_for_empty_category(self, app_ctx):
        category = Category(id="empty", name="Пустая", order=2)
        db.session.add(category)
        db.session.commit()

        payload = category.to_dict()

        assert payload["sign_count"] == 0

    def test_to_dict_serializes_dates_as_iso_with_z(self, app_ctx):
        category = Category(
            id="dates",
            name="Даты",
            order=3,
            created_at=datetime(2026, 4, 13, 8, 15, 1, 123456),
            updated_at=datetime(2026, 4, 13, 9, 16, 2, 654321),
        )
        db.session.add(category)
        db.session.commit()

        payload = category.to_dict()

        assert payload["created_at"] == "2026-04-13T08:15:01.123456Z"
        assert payload["updated_at"] == "2026-04-13T09:16:02.654321Z"
