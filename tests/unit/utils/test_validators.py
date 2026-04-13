"""Unit tests for DB-aware validators."""
from __future__ import annotations

from types import SimpleNamespace

from app.constants import MAX_CATEGORY_NAME_LENGTH, MAX_WORD_LENGTH, VIDEO_MAX_SIZE
from app.database import db
from app.models.category import Category
from app.utils.validators import (
    validate_category_data,
    validate_entity_exists,
    validate_lesson_data,
    validate_sign_data,
    validate_video_data,
)


def test_validate_sign_data_accepts_valid_payload():
    errors = validate_sign_data(
        {
            "word": "привет",
            "category_id": "greetings",
            "description": "Описание",
        }
    )

    assert errors == []


def test_validate_sign_data_rejects_empty_word_too_long_word_and_invalid_category_id():
    errors = validate_sign_data(
        {
            "word": "",
            "category_id": "",
        }
    )
    long_word_errors = validate_sign_data(
        {
            "word": "а" * (MAX_WORD_LENGTH + 1),
            "category_id": "c" * 51,
        }
    )

    assert 'Поле "word" должно быть непустой строкой' in errors
    assert 'Поле "category_id" должно быть непустой строкой' in errors
    assert f'Поле "word" не должно превышать {MAX_WORD_LENGTH} символов' in long_word_errors
    assert 'Поле "category_id" не должно превышать 50 символов' in long_word_errors


def test_validate_category_data_accepts_valid_payload():
    errors = validate_category_data({"name": "Приветствия", "order": 1})

    assert errors == []


def test_validate_category_data_rejects_invalid_name_and_order():
    errors = validate_category_data({"name": "", "order": "1"})
    overflow_errors = validate_category_data(
        {"name": "а" * (MAX_CATEGORY_NAME_LENGTH + 1), "order": -1}
    )

    assert 'Поле "name" должно быть непустой строкой' in errors
    assert 'Поле "order" должно быть целым числом' in errors
    assert f'Поле "name" не должно превышать {MAX_CATEGORY_NAME_LENGTH} символов' in overflow_errors
    assert 'Поле "order" должно быть неотрицательным' in overflow_errors


def test_validate_video_data_rejects_invalid_file_and_payload():
    file_obj = SimpleNamespace(filename="", content_length=VIDEO_MAX_SIZE + 1)

    errors = validate_video_data(
        {"context_description": "", "order": "1"},
        file=file_obj,
    )

    assert "Файл не указан" in errors
    assert 'Размер файла не должен превышать 50MB' in errors
    assert 'Поле "context_description" должно быть непустой строкой' in errors
    assert 'Поле "order" должно быть целым числом' in errors


def test_validate_video_data_rejects_non_mp4_file():
    file_obj = SimpleNamespace(filename="video.avi", content_length=1024)

    errors = validate_video_data({"context_description": "Контекст", "order": 0}, file=file_obj)

    assert errors == ["Поддерживается только формат MP4"]


def test_validate_lesson_data_supports_require_id_and_require_video_flags():
    is_valid_create, create_error = validate_lesson_data(
        {
            "title": "Урок",
            "description": "Описание",
            "order": 1,
        },
        require_id=False,
        require_video=False,
    )
    is_valid_update, update_error = validate_lesson_data(
        {
            "id": "lesson_1",
            "title": "Урок",
            "description": "Описание",
            "video_url": "lessons/lesson-1.mp4",
            "order": 1,
        },
        require_id=True,
        require_video=True,
    )

    assert (is_valid_create, create_error) == (True, "")
    assert (is_valid_update, update_error) == (True, "")


def test_validate_lesson_data_rejects_invalid_order_and_missing_required_fields():
    assert validate_lesson_data(
        {"description": "Описание", "video_url": "x.mp4", "order": 1},
        require_id=False,
        require_video=True,
    ) == (False, "Title обязателен и должен быть не длиннее 200 символов")
    assert validate_lesson_data(
        {"title": "Урок", "video_url": "x.mp4", "order": 1},
        require_id=False,
        require_video=True,
    ) == (False, "Description обязателен")
    assert validate_lesson_data(
        {"title": "Урок", "description": "Описание", "order": 1},
        require_id=False,
        require_video=True,
    ) == (False, "Video URL обязателен при создании урока")
    assert validate_lesson_data(
        {"title": "Урок", "description": "Описание", "order": "1"},
        require_id=False,
        require_video=False,
    ) == (False, "Order должен быть неотрицательным целым числом")
    assert validate_lesson_data(
        {"title": "Урок", "description": "Описание", "order": -1},
        require_id=False,
        require_video=False,
    ) == (False, "Order должен быть неотрицательным целым числом")
    assert validate_lesson_data(
        {"title": "Урок", "description": "Описание", "order": 1},
        require_id=True,
        require_video=False,
    ) == (False, "ID обязателен и должен быть не длиннее 50 символов")


def test_validate_entity_exists_returns_entity_when_found(app_ctx):
    category = Category(id="cat_1", name="Категория", order=1)
    db.session.add(category)
    db.session.commit()

    entity, error = validate_entity_exists(Category, "cat_1")

    assert entity == category
    assert error is None


def test_validate_entity_exists_returns_error_response_when_missing(app_ctx):
    entity, error = validate_entity_exists(Category, "missing")

    assert entity is None
    response, status_code = error
    assert status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "CATEGORY_NOT_FOUND",
            "message": "Category не найдена",
        },
    }
