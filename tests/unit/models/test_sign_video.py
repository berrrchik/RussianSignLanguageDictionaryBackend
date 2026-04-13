"""Тесты сериализации SignVideo."""
from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo


class TestSignVideoSerialization:
    """Проверки to_dict() и to_dict_local()."""

    def test_to_dict_uses_default_description_for_primary_video(self, app_ctx):
        video = SignVideo(
            sign_id="sign_1",
            file_path="signs/cat_1/video.mp4",
            url="http://example.com/video.mp4",
            context_description=None,
            order=0,
        )

        payload = video.to_dict()

        assert payload["context_description"] == "Основное видео"

    def test_to_dict_uses_incremented_description_for_secondary_video(self, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", category_id="cat_1")
        video = SignVideo(
            sign_id="sign_1",
            file_path="signs/cat_1/video.mp4",
            url="http://example.com/video.mp4",
            context_description=" ",
            order=2,
        )
        db.session.add_all([category, sign, video])
        db.session.commit()

        payload = video.to_dict()

        assert payload["context_description"] == "Видео 3"

    def test_to_dict_preserves_existing_description(self, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", category_id="cat_1")
        video = SignVideo(
            sign_id="sign_1",
            file_path="signs/cat_1/video.mp4",
            url="http://example.com/video.mp4",
            context_description="Кастомное описание",
            order=0,
        )
        db.session.add_all([category, sign, video])
        db.session.commit()

        payload = video.to_dict()

        assert payload["context_description"] == "Кастомное описание"

    def test_to_dict_local_builds_url_from_relative_file_path(self, app, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", category_id="cat_1")
        video = SignVideo(
            sign_id="sign_1",
            file_path="signs/cat_1/video.mp4",
            url="http://example.com/video.mp4",
            context_description="Контекст",
            order=0,
        )
        db.session.add_all([category, sign, video])
        db.session.commit()

        with app.app_context():
            payload = video.to_dict_local()

        assert payload["url"] == "http://testserver.local/videos/signs/cat_1/video.mp4"

    def test_to_dict_local_keeps_absolute_file_path_compatible(self, app, app_ctx, tmp_video_storage_config):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", category_id="cat_1")
        absolute_file_path = f"{tmp_video_storage_config['VIDEO_STORAGE_PATH']}/signs/cat_1/video.mp4"
        video = SignVideo(
            sign_id="sign_1",
            file_path=absolute_file_path,
            url="http://example.com/video.mp4",
            context_description="Контекст",
            order=0,
        )
        db.session.add_all([category, sign, video])
        db.session.commit()

        with app.app_context():
            payload = video.to_dict_local()

        assert payload["url"] == f"http://testserver.local/videos/{absolute_file_path.lstrip('/')}"

    def test_to_dict_and_to_dict_local_serialize_dates(self, app, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", category_id="cat_1")
        video = SignVideo(
            sign_id="sign_1",
            file_path="signs/cat_1/video.mp4",
            url="http://example.com/video.mp4",
            context_description="Контекст",
            order=0,
            created_at=datetime(2026, 4, 13, 8, 0, 0, 123456),
            updated_at=datetime(2026, 4, 13, 9, 0, 0, 654321),
        )
        db.session.add_all([category, sign, video])
        db.session.commit()

        payload = video.to_dict()
        with app.app_context():
            local_payload = video.to_dict_local()

        assert payload["created_at"] == "2026-04-13T08:00:00.123456Z"
        assert payload["updated_at"] == "2026-04-13T09:00:00.654321Z"
        assert local_payload["created_at"] == "2026-04-13T08:00:00.123456Z"
        assert local_payload["updated_at"] == "2026-04-13T09:00:00.654321Z"
