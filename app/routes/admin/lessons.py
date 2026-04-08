"""
Endpoints для управления уроками.
"""
import os
from pathlib import Path
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app

from app.database import db
from app.models.lesson import Lesson
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.validators import validate_lesson_data
from app.utils.decorators import handle_db_errors, require_json
from app.utils.responses import (
    success_response,
    error_response,
)
from app.utils.id_generator import generate_lesson_id
from app.utils.metrics import admin_lesson_operations
from app.utils.logging_config import get_logger, log_business_event

bp = Blueprint('admin_lessons', __name__)
logger = get_logger(__name__)


def _is_local_video_storage() -> bool:
    """Проверяет, используется ли локальное хранилище видео."""
    return os.getenv('VIDEO_STORAGE_TYPE', 'local').lower() == 'local'


def _lesson_filename(lesson_id: str) -> str:
    """Формирует имя файла урока: lesson-N.mp4."""
    return lesson_id.replace('_', '-') + '.mp4'


def _lesson_relative_path(lesson_id: str) -> str:
    """Относительный путь к видео урока внутри VIDEO_STORAGE_PATH."""
    return f"lessons/{_lesson_filename(lesson_id)}"


def _lesson_absolute_path(lesson_id: str) -> Path:
    """Абсолютный путь к видео урока на диске."""
    base_path = Path(current_app.config['VIDEO_STORAGE_PATH'])
    return base_path / _lesson_relative_path(lesson_id)


@bp.route('/lessons', methods=['GET'])
@require_auth
@handle_db_errors('получения списка уроков')
def get_lessons() -> Tuple[Dict[str, Any], int]:
    """
    Получение списка всех уроков
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    responses:
      200:
        description: Список уроков, отсортированных по order
    """
    lessons = Lesson.query.order_by(Lesson.order).all()
    return success_response(data=[lesson.to_dict() for lesson in lessons])


@bp.route('/lessons/<string:lesson_id>', methods=['GET'])
@require_auth
@handle_db_errors('получения урока')
def get_lesson(lesson_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение урока по ID
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: lesson_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Данные урока
      404:
        description: Урок не найден
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    return success_response(data=lesson.to_dict())


@bp.route('/lessons', methods=['POST'])
@require_auth
@require_json
@handle_db_errors('создания урока')
def create_lesson() -> Tuple[Dict[str, Any], int]:
    """
    Создание нового урока
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - title
            - description
            - video_url
            - order
          properties:
            id:
              type: string
              description: Опционально, будет автогенерирован если не указан
            title:
              type: string
              example: "Раздел ЭТО ВАЖНО"
            description:
              type: string
              example: "Описание урока"
            video_url:
              type: string
              example: "lessons/lesson-1.mp4"
              description: "Путь к видео (с дефисом, не подчеркиванием - Supabase не поддерживает подчеркивания)"
            order:
              type: integer
              example: 1
    responses:
      201:
        description: Урок создан
      400:
        description: Ошибка валидации
      409:
        description: Урок с таким ID уже существует
    """
    data = request.get_json()
    
    # Валидация (ID опционален при создании, но video_url обязателен)
    is_valid, error_msg = validate_lesson_data(data, require_id=False, require_video=True)
    if not is_valid:
        return error_response('VALIDATION_ERROR', error_msg, 400)
    
    # Автогенерация ID если не указан
    if not data.get('id'):
        data['id'] = generate_lesson_id()
    
    # Автогенерация порядка если не указан
    if data.get('order') is None:
        from sqlalchemy import func
        max_order = db.session.query(func.max(Lesson.order)).scalar()
        data['order'] = (max_order or 0) + 1
    
    # video_url должен быть указан (обязательное поле при создании)
    if not data.get('video_url'):
        return error_response('VALIDATION_ERROR', 'Video URL обязателен при создании урока', 400)
    
    # Проверка уникальности ID
    if Lesson.query.get(data['id']):
        return error_response('DUPLICATE_ID', f"Урок с ID '{data['id']}' уже существует", 409)
    
    # Создание урока
    lesson = Lesson(**data)
    db.session.add(lesson)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_lesson_operations.labels(operation='create').inc()
    
    log_business_event(logger, "Lesson created", {
        "lesson_id": lesson.id,
        "title": lesson.title
    }, event_domain="admin_content", event_name="lesson_created", resource="lesson", action="create", outcome="success")
    
    return success_response(data=lesson.to_dict(), status_code=201)


@bp.route('/lessons/<string:lesson_id>', methods=['PUT'])
@require_auth
@require_json
@handle_db_errors('обновления урока')
def update_lesson(lesson_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Обновление урока
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: lesson_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            title:
              type: string
              example: "Раздел 1"
            description:
              type: string
              example: "Описание урока"
            video_url:
              type: string
              example: "lessons/lesson-1.mp4"
            order:
              type: integer
              example: 1
    responses:
      200:
        description: Урок обновлен
      400:
        description: Ошибка валидации
      404:
        description: Урок не найден
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    data = request.get_json()
    
    # Валидация (ID обязателен при обновлении, но берется из URL)
    # Добавляем ID в данные для валидации
    validation_data = data.copy()
    validation_data['id'] = lesson_id
    is_valid, error_msg = validate_lesson_data(validation_data, require_id=True)
    if not is_valid:
        return error_response('VALIDATION_ERROR', error_msg, 400)
    
    # Обновление полей (ID не изменяется). order приводим к int (Swagger может прислать "string").
    for key, value in data.items():
        if key == 'id':
            continue
        if key == 'order':
            try:
                value = int(value)
            except (TypeError, ValueError):
                return error_response('VALIDATION_ERROR', 'Поле order должно быть целым числом', 400)
        setattr(lesson, key, value)
    
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_lesson_operations.labels(operation='update').inc()
    
    log_business_event(logger, "Lesson updated", {
        "lesson_id": lesson_id
    }, event_domain="admin_content", event_name="lesson_updated", resource="lesson", action="update", outcome="success")
    
    return success_response(data=lesson.to_dict())


@bp.route('/lessons/<string:lesson_id>', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления урока')
def delete_lesson(lesson_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Удаление урока
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: lesson_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Урок удален
      404:
        description: Урок не найден
    """
    lesson = Lesson.query.get_or_404(lesson_id)

    # Удаляем связанный видеофайл, если он есть
    if lesson.video_url:
        if _is_local_video_storage():
            try:
                file_path = _lesson_absolute_path(lesson.id)
                if file_path.exists():
                    file_path.unlink()
                    current_app.logger.info(f"Видео урока удалено из локального хранилища: {file_path}")
            except Exception as e:
                current_app.logger.warning(f"Ошибка при удалении локального видео урока: {e}")
                # Продолжаем удаление урока, даже если файл удалить не удалось
        else:
            try:
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
                bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')

                if supabase_url and supabase_key:
                    try:
                        from supabase import create_client, Client
                        supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
                        storage_path = _lesson_filename(lesson.id)
                        try:
                            supabase.storage.from_(bucket_name).remove([storage_path])
                            current_app.logger.info(f"Видео {storage_path} удалено из Supabase Storage")
                        except Exception as e:
                            current_app.logger.warning(f"Не удалось удалить файл {storage_path} из Supabase: {e}")
                    except ImportError:
                        current_app.logger.warning("Библиотека supabase не установлена, видео не удалено из Storage")
            except Exception as e:
                current_app.logger.warning(f"Ошибка при удалении видео из Supabase Storage: {e}")
                # Продолжаем удаление урока, даже если удалить файл не удалось
    
    # Удаляем урок из базы данных
    db.session.delete(lesson)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_lesson_operations.labels(operation='delete').inc()
    
    log_business_event(logger, "Lesson deleted", {
        "lesson_id": lesson_id
    }, event_domain="admin_content", event_name="lesson_deleted", resource="lesson", action="delete", outcome="success")
    
    return success_response(message='Урок удален')


@bp.route('/lessons/<string:lesson_id>/video', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления видео урока')
def delete_lesson_video(lesson_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Удаление видео урока
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: lesson_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Видео удалено
      404:
        description: Урок не найден
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if not lesson.video_url:
        return error_response('NO_VIDEO', 'У урока нет видео для удаления', 400)
    
    try:
        if _is_local_video_storage():
            file_path = _lesson_absolute_path(lesson.id)
            if file_path.exists():
                file_path.unlink()
        else:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')

            if not supabase_url or not supabase_key:
                return error_response('CONFIG_ERROR', 'Настройки Supabase не найдены. Укажите SUPABASE_URL и SUPABASE_KEY (или SUPABASE_SERVICE_ROLE_KEY) в .env', 500)

            try:
                from supabase import create_client, Client
            except ImportError:
                return error_response('DEPENDENCY_ERROR', 'Библиотека supabase не установлена. Установите: pip install supabase', 500)

            supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
            storage_path = _lesson_filename(lesson.id)
            try:
                supabase.storage.from_(bucket_name).remove([storage_path])
            except Exception as e:
                current_app.logger.warning(f"Не удалось удалить файл {storage_path} из Supabase: {e}")

        # Обновляем video_url в базе данных (устанавливаем пустое значение)
        lesson.video_url = ''
        db.session.commit()

        # Обновление метаданных синхронизации
        update_sync_metadata()

        log_business_event(
            logger,
            "Lesson video deleted",
            {"lesson_id": lesson_id},
            event_domain="admin_content",
            event_name="lesson_video_deleted",
            resource="lesson_video",
            action="delete",
            outcome="success",
        )

        return success_response(message='Видео удалено успешно')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при удалении видео урока {lesson_id}: {e}")
        return error_response('DELETE_ERROR', f'Ошибка при удалении видео: {e}', 500)


@bp.route('/lessons/<string:lesson_id>/video', methods=['POST'])
@require_auth
@handle_db_errors('загрузки видео урока')
def upload_lesson_video(lesson_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Загрузка видео для урока
    ---
    tags:
      - Уроки
    security:
      - Bearer: []
    parameters:
      - name: lesson_id
        in: path
        type: string
        required: true
      - name: file
        in: formData
        type: file
        required: true
        description: MP4 видео файл (макс. 50MB)
    responses:
      200:
        description: Видео загружено и URL обновлен
      400:
        description: Ошибка валидации
      404:
        description: Урок не найден
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if 'file' not in request.files:
        return error_response('NO_FILE', 'Файл не загружен', 400)
    
    file = request.files['file']
    if not file.filename:
        return error_response('NO_FILE', 'Файл не выбран', 400)
    
    # Валидация файла
    if not file.filename.lower().endswith('.mp4'):
        return error_response('INVALID_FILE', 'Только файлы MP4 разрешены', 400)
    
    if file.content_length and file.content_length > 50 * 1024 * 1024:
        return error_response('FILE_TOO_LARGE', 'Размер файла не должен превышать 50MB', 400)
    
    try:
        filename = _lesson_filename(lesson.id)

        if _is_local_video_storage():
            full_path = _lesson_absolute_path(lesson.id)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            file.save(str(full_path))
            video_url = f"/lessons/{filename}"
        else:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')

            if not supabase_url or not supabase_key:
                return error_response('CONFIG_ERROR', 'Настройки Supabase не найдены. Укажите SUPABASE_URL и SUPABASE_KEY (или SUPABASE_SERVICE_ROLE_KEY) в .env', 500)

            try:
                from supabase import create_client, Client
            except ImportError:
                return error_response('DEPENDENCY_ERROR', 'Библиотека supabase не установлена. Установите: pip install supabase', 500)

            supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
            storage_path = filename
            file.seek(0)
            file_data = file.read()
            supabase.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
            video_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)

        # Обновляем video_url в уроке
        lesson.video_url = video_url
        db.session.commit()

        # Обновление метаданных синхронизации
        update_sync_metadata()

        log_business_event(
            logger,
            "Lesson video uploaded",
            {"lesson_id": lesson_id, "video_url": video_url},
            event_domain="admin_content",
            event_name="lesson_video_uploaded",
            resource="lesson_video",
            action="upload",
            outcome="success",
        )

        return success_response(data={'video_url': video_url}, message='Видео загружено успешно')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Ошибка загрузки видео урока: {str(e)}')
        return error_response('UPLOAD_ERROR', f'Ошибка загрузки видео: {str(e)}', 500)
