"""
Endpoints для управления уроками.
"""
import os
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

bp = Blueprint('admin_lessons', __name__)


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
            description:
              type: string
            video_url:
              type: string
            order:
              type: integer
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
    
    # Обновление полей (ID не изменяется)
    for key, value in data.items():
        if key != 'id':  # ID не изменяется
            setattr(lesson, key, value)
    
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
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
    
    # Удаляем видео из Supabase Storage, если оно есть
    if lesson.video_url:
        try:
            # Получаем настройки Supabase из переменных окружения
            supabase_url = os.getenv('SUPABASE_URL')
            # Используем service role key для удаления (обходит RLS), если доступен, иначе anon key
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')
            
            if supabase_url and supabase_key:
                # Импортируем Supabase клиент
                try:
                    from supabase import create_client, Client
                    
                    # Создаем клиент Supabase (URL должен быть без trailing slash)
                    supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
                    
                    # Формируем имя файла: lesson-N.mp4 (с дефисом для Supabase)
                    filename = lesson.id.replace('_', '-') + '.mp4'
                    storage_path = filename  # В bucket lessons файлы хранятся прямо в корне
                    
                    # Удаляем файл из Supabase Storage
                    try:
                        supabase.storage.from_(bucket_name).remove([storage_path])
                        current_app.logger.info(f"Видео {storage_path} удалено из Supabase Storage")
                    except Exception as e:
                        current_app.logger.warning(f"Не удалось удалить файл {storage_path} из Supabase: {e}")
                        # Продолжаем удаление урока, даже если файл не найден в хранилище
                except ImportError:
                    current_app.logger.warning("Библиотека supabase не установлена, видео не удалено из Storage")
        except Exception as e:
            current_app.logger.warning(f"Ошибка при удалении видео из Supabase Storage: {e}")
            # Продолжаем удаление урока, даже если не удалось удалить видео
    
    # Удаляем урок из базы данных
    db.session.delete(lesson)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
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
        # Получаем настройки Supabase из переменных окружения
        supabase_url = os.getenv('SUPABASE_URL')
        # Используем service role key для удаления (обходит RLS), если доступен, иначе anon key
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')
        
        if not supabase_url or not supabase_key:
            return error_response('CONFIG_ERROR', 'Настройки Supabase не найдены. Укажите SUPABASE_URL и SUPABASE_KEY (или SUPABASE_SERVICE_ROLE_KEY) в .env', 500)
        
        # Импортируем Supabase клиент
        try:
            from supabase import create_client, Client
        except ImportError:
            return error_response('DEPENDENCY_ERROR', 'Библиотека supabase не установлена. Установите: pip install supabase', 500)
        
        # Создаем клиент Supabase (URL должен быть без trailing slash)
        supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
        
        if lesson.video_url.startswith('http://') or lesson.video_url.startswith('https://'):
            try:
                storage_path = lesson.video_url.split('/')[-1]
            except Exception:
                storage_path = lesson.id.replace('_', '-') + '.mp4'
        elif lesson.video_url.startswith('lessons/'):
            storage_path = lesson.video_url.replace('lessons/', '')
        else:
            storage_path = lesson.id.replace('_', '-') + '.mp4'
        
        # Удаляем файл из Supabase Storage
        try:
            supabase.storage.from_(bucket_name).remove([storage_path])
        except Exception as e:
            current_app.logger.warning(f"Не удалось удалить файл {storage_path} из Supabase: {e}")
            # Продолжаем, даже если файл не найден в хранилище
        
        # Обновляем video_url в базе данных (устанавливаем пустое значение)
        lesson.video_url = ''
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
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
        # Получаем настройки Supabase из переменных окружения
        supabase_url = os.getenv('SUPABASE_URL')
        # Используем service role key для загрузки (обходит RLS), если доступен, иначе anon key
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        bucket_name = os.getenv('SUPABASE_LESSONS_BUCKET', 'lessons')
        
        if not supabase_url or not supabase_key:
            return error_response('CONFIG_ERROR', 'Настройки Supabase не найдены. Укажите SUPABASE_URL и SUPABASE_KEY (или SUPABASE_SERVICE_ROLE_KEY) в .env', 500)
        
        # Импортируем Supabase клиент
        try:
            from supabase import create_client, Client
        except ImportError:
            return error_response('DEPENDENCY_ERROR', 'Библиотека supabase не установлена. Установите: pip install supabase', 500)
        
        # Создаем клиент Supabase (URL должен быть без trailing slash)
        supabase: Client = create_client(supabase_url.rstrip('/'), supabase_key)
        
        # Формируем имя файла: lesson-N.mp4 (с дефисом для Supabase)
        filename = lesson.id.replace('_', '-') + '.mp4'
        storage_path = filename  # В bucket lessons файлы хранятся прямо в корне
        
        # Читаем файл
        file.seek(0)
        file_data = file.read()
        
        # Загружаем в Supabase Storage
        supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "video/mp4", "upsert": "true"}
        )
        
        # Получаем публичный URL (полный URL)
        public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
        
        # Сохраняем полный URL в базу данных
        video_url = public_url
        
        # Обновляем video_url в уроке
        lesson.video_url = video_url
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(data={'video_url': video_url}, message='Видео загружено успешно')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Ошибка загрузки видео урока: {str(e)}')
        return error_response('UPLOAD_ERROR', f'Ошибка загрузки видео: {str(e)}', 500)
