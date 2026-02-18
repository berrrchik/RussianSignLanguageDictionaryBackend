"""
Endpoints для синхронизации мобильного приложения.

Raw эндпоинты возвращают данные без обертки {success, data, message}
с Unix timestamp датами (оптимизировано для мобильных клиентов).
"""
from typing import Tuple, Dict, Any, List
from flask import Blueprint, request, current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.lesson import Lesson
from app.models.responses import (
    SyncMetadataRawResponse,
    SyncDataRawResponse,
    CategoryRawResponse,
    SignRawResponse,
    SignVideoRawResponse,
    SynonymRawResponse,
    LessonRawResponse,
)
from app.utils.sorting import sort_signs_russian
from app.utils.serializers import deserialize_datetime
from app.utils.error_handlers import raw_error_handler
from app.utils.etag import create_response_with_etag
from app.utils.sync import get_or_create_sync_metadata
from app.utils.synonyms import get_sign_synonyms
from app.utils.metrics import (
    sync_check_total,
    sync_data_total,
    sync_data_size,
    sync_duration
)
from app.utils.logging_config import get_logger, log_business_event

bp = Blueprint('sync', __name__)
logger = get_logger(__name__)


def _build_sign_raw_response(sign: Sign) -> SignRawResponse:
    """
    Строит SignRawResponse из модели Sign с видео и синонимами.
    
    Args:
        sign: Объект Sign из БД
        
    Returns:
        SignRawResponse с видео и синонимами
    """
    synonyms_data = get_sign_synonyms(sign.id)
    synonyms: List[SynonymRawResponse] = [
        SynonymRawResponse(id=s['id'], word=s['word']) for s in synonyms_data
    ]
    
    videos: List[SignVideoRawResponse] = []
    for video in sign.videos:
        context_desc = video.context_description
        if not context_desc or (isinstance(context_desc, str) and context_desc.strip() == ''):
            context_desc = f"Видео {video.order + 1}" if video.order > 0 else "Основное видео"
        
        videos.append(SignVideoRawResponse(
            id=video.id,
            url=video.url,
            context_description=context_desc,
            order=video.order,
            created_at=video.created_at,
            updated_at=video.updated_at,
        ))
    
    return SignRawResponse(
        id=sign.id,
        word=sign.word,
        description=sign.description,
        category_id=sign.category_id,
        videos=videos,
        synonyms=synonyms,
        created_at=sign.created_at,
        updated_at=sign.updated_at,
    )


@bp.route('/check/raw', methods=['GET'])
@raw_error_handler
def check_updates_raw() -> Tuple[Dict[str, Any], int]:
    """
    Проверка наличия обновлений (упрощенный формат без обертки)
    ---
    tags:
      - Синхронизация (Raw)
    parameters:
      - name: last_updated
        in: query
        type: integer
        required: false
        description: Unix timestamp (секунды) последнего обновления на клиенте
        example: 1705318245
    responses:
      200:
        description: Информация об обновлениях
        schema:
          type: object
          properties:
            last_updated:
              type: integer
              description: Unix timestamp последнего обновления на сервере
              example: 1705318245
            has_updates:
              type: boolean
              example: true
      400:
        description: Ошибка валидации
        schema:
          type: object
          properties:
            error:
              type: string
              example: "ValidationError"
            message:
              type: string
              example: "Invalid timestamp format"
      500:
        description: Внутренняя ошибка сервера
    """
    current_app.logger.info("Raw endpoint accessed: /check/raw")
    
    client_timestamp_str = request.args.get('last_updated')
    metadata = get_or_create_sync_metadata()
    
    has_updates = True
    if client_timestamp_str:
        try:
            client_timestamp = int(client_timestamp_str)
            client_dt = deserialize_datetime(client_timestamp)
            
            server_dt = metadata.last_updated
            if server_dt.tzinfo:
                server_dt = server_dt.replace(tzinfo=None)
            if client_dt.tzinfo:
                client_dt = client_dt.replace(tzinfo=None)
            
            has_updates = server_dt > client_dt
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {client_timestamp_str}")
    
    response = SyncMetadataRawResponse(
        last_updated=metadata.last_updated,
        has_updates=has_updates
    )
    
    # Добавляем метрику и логирование
    sync_check_total.labels(has_updates=str(has_updates)).inc()
    
    log_business_event(logger, "Sync check requested", {
        "has_updates": has_updates,
        "last_updated": metadata.last_updated.timestamp() if metadata.last_updated else None,
        "client_timestamp": client_timestamp_str
    })
    
    data = response.model_dump()
    
    # Используем утилиту для ETag
    return create_response_with_etag(data, "/sync/check/raw")


@bp.route('/data/raw', methods=['GET'])
@raw_error_handler
def get_all_data_raw() -> Tuple[Dict[str, Any], int]:
    """
    Получение всех данных для синхронизации (упрощенный формат без обертки)
    ---
    tags:
      - Синхронизация (Raw)
    responses:
      200:
        description: Все данные для синхронизации
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  order:
                    type: integer
                  sign_count:
                    type: integer
                  created_at:
                    type: integer
                    description: Unix timestamp
                  updated_at:
                    type: integer
                    description: Unix timestamp
            signs:
              type: array
              items:
                type: object
            lessons:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  title:
                    type: string
                  description:
                    type: string
                  video_url:
                    type: string
                  order:
                    type: integer
                  created_at:
                    type: integer
                    description: Unix timestamp
                  updated_at:
                    type: integer
                    description: Unix timestamp
            last_updated:
              type: integer
              description: Unix timestamp последнего обновления
              example: 1705318245
      500:
        description: Внутренняя ошибка сервера
    """
    # Логируем использование raw endpoint для аналитики миграции
    current_app.logger.info("Raw endpoint accessed: /data/raw")
    
    # Используем декоратор для измерения времени синхронизации
    with sync_duration.time():
        # Получаем категории
        categories = Category.query.order_by(Category.order).all()
    
    # Получаем жесты с видео
    signs = Sign.query.options(
        joinedload(Sign.videos)
    ).order_by(func.lower(Sign.word)).all()
    
    sorted_signs = sort_signs_russian(signs)
    
    # Получаем уроки
    lessons = Lesson.query.order_by(Lesson.order).all()
    
    # Валидация данных
    signs_without_videos = [s for s in sorted_signs if not s.videos]
    if signs_without_videos:
        current_app.logger.warning(
            f"Найдено {len(signs_without_videos)} жестов без видео: "
            f"{[s.id for s in signs_without_videos[:5]]}"
        )
    
    # Получение метаданных
    metadata = get_or_create_sync_metadata()
    
    # Строим response модели
    categories_response = [
        CategoryRawResponse(
            id=cat.id,
            name=cat.name,
            order=cat.order,
            sign_count=len(cat.signs) if cat.signs else 0,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        for cat in categories
    ]
    
    signs_response = [_build_sign_raw_response(sign) for sign in sorted_signs]
    
    lessons_response = [
        LessonRawResponse(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            video_url=lesson.video_url,
            order=lesson.order,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )
        for lesson in lessons
    ]
    
    response = SyncDataRawResponse(
        categories=categories_response,
        signs=signs_response,
        lessons=lessons_response,
        last_updated=metadata.last_updated
    )
        
        # Добавляем метрики
        sync_data_total.inc()
        sync_data_size.labels(data_type='categories').observe(len(categories_response))
        sync_data_size.labels(data_type='signs').observe(len(signs_response))
        sync_data_size.labels(data_type='lessons').observe(len(lessons_response))
        
        log_business_event(logger, "Full sync completed", {
            "categories_count": len(categories_response),
            "signs_count": len(signs_response),
            "lessons_count": len(lessons_response)
        })
    
    # Создаем словарь данных для генерации ETag (точно как в ответе)
    data = response.model_dump()
    
    # Логируем для отладки перед генерацией ETag
    current_app.logger.debug(
        f"ETag generation for /sync/data/raw: "
        f"categories={len(data.get('categories', []))}, "
        f"signs={len(data.get('signs', []))}, "
        f"lessons={len(data.get('lessons', []))}, "
        f"last_updated={data.get('last_updated')}"
    )
    
    # Используем утилиту для ETag
    return create_response_with_etag(data, "/sync/data/raw")


