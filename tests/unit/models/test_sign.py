"""Тесты сериализации Sign."""
from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.models.sign_video import SignVideo


class TestSignSerialization:
    """Проверки Sign.to_dict() и Sign.to_dict_with_relations()."""

    def test_to_dict_returns_videos_count(self, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_1", word="слово", description="", category_id="cat_1")
        db.session.add_all([category, sign])
        db.session.add_all(
            [
                SignVideo(
                    sign_id="sign_1",
                    file_path="signs/cat_1/video-1.mp4",
                    url="http://example.com/video-1.mp4",
                    context_description="Первое видео",
                    order=0,
                ),
                SignVideo(
                    sign_id="sign_1",
                    file_path="signs/cat_1/video-2.mp4",
                    url="http://example.com/video-2.mp4",
                    context_description="Второе видео",
                    order=1,
                ),
            ]
        )
        db.session.commit()

        payload = sign.to_dict()

        assert payload["id"] == "sign_1"
        assert payload["word"] == "слово"
        assert payload["videos_count"] == 2

    def test_to_dict_with_relations_includes_sorted_videos_and_synonyms(self, app, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(
            id="sign_1",
            word="привет",
            description=None,
            category_id="cat_1",
            created_at=datetime(2026, 4, 13, 10, 0, 0),
            updated_at=datetime(2026, 4, 13, 11, 0, 0),
        )
        synonym = Sign(id="sign_2", word="здравствуй", description="синоним", category_id="cat_1")
        db.session.add_all([category, sign, synonym])
        db.session.flush()

        db.session.add_all(
            [
                SignVideo(
                    sign_id="sign_1",
                    file_path="signs/cat_1/video-2.mp4",
                    url="http://example.com/video-2.mp4",
                    context_description="Второе",
                    order=1,
                ),
                SignVideo(
                    sign_id="sign_1",
                    file_path="signs/cat_1/video-1.mp4",
                    url="http://example.com/video-1.mp4",
                    context_description="",
                    order=0,
                ),
            ]
        )
        db.session.add(SignSynonym(sign_id_1="sign_1", sign_id_2="sign_2"))
        db.session.commit()

        with app.app_context():
            payload = sign.to_dict_with_relations()

        assert payload["description"] is None
        assert [video["order"] for video in payload["videos"]] == [0, 1]
        assert payload["videos"][0]["url"] == "http://testserver.local/videos/signs/cat_1/video-1.mp4"
        assert payload["videos"][0]["context_description"] == "Основное видео"
        assert payload["synonyms"] == [{"id": "sign_2", "word": "здравствуй"}]
        assert payload["created_at"] == "2026-04-13T10:00:00Z"
        assert payload["updated_at"] == "2026-04-13T11:00:00Z"

    def test_to_dict_with_relations_deduplicates_bidirectional_synonyms(self, app, app_ctx):
        category = Category(id="cat_1", name="Категория", order=1)
        sign = Sign(id="sign_a", word="А", category_id="cat_1")
        synonym = Sign(id="sign_b", word="Б", category_id="cat_1")
        db.session.add_all([category, sign, synonym])
        db.session.flush()
        db.session.add_all(
            [
                SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"),
                SignSynonym(sign_id_1="sign_b", sign_id_2="sign_a"),
            ]
        )
        db.session.commit()

        with app.app_context():
            payload = sign.to_dict_with_relations()

        assert payload["synonyms"] == [{"id": "sign_b", "word": "Б"}]
