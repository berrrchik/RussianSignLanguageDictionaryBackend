"""
Endpoints для синхронизации мобильного приложения.

Содержит два набора эндпоинтов:
- Legacy: /check, /data - с оберткой {success, data, message} и ISO 8601 датами
- Raw: /check/raw, /data/raw - без обертки с Unix timestamp датами (оптимизировано для мобильных)
"""
from datetime import datetime
from typing import Tuple, Dict, Any, List
from flask import Blueprint, request, current_app, jsonify
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.models.sync_metadata import SyncMetadata
from app.models.responses import (
    SyncMetadataRawResponse,
    SyncDataRawResponse,
    CategoryRawResponse,
    SignRawResponse,
    SignVideoRawResponse,
    SynonymRawResponse,
)
from app.utils.responses import success_response, internal_error_response
from app.utils.sorting import sort_signs_russian
from app.utils.formatters import format_datetime
from app.utils.serializers import serialize_datetime, deserialize_datetime
from app.utils.error_handlers import raw_error_handler

bp = Blueprint('sync', __name__)


@bp.route('/check', methods=['GET'])
def check_updates() -> Tuple[Dict[str, Any], int]:
    """
    Проверка наличия обновлений
    ---
    tags:
      - Синхронизация
    parameters:
      - name: last_updated
        in: query
        type: string
        required: false
        description: ISO 8601 timestamp последнего обновления на клиенте
        example: "2025-01-15T10:30:00Z"
    responses:
      200:
        description: Информация об обновлениях
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                last_updated:
                  type: string
                  example: "2025-01-15T10:30:00Z"
                has_updates:
                  type: boolean
                  example: true
    """
    try:
        client_timestamp = request.args.get('last_updated')
        metadata = SyncMetadata.query.first()
        
        if not metadata:
            # Если метаданных нет, создаём их
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        has_updates = True
        if client_timestamp:
            try:
                client_dt = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                # Преобразование в UTC если нужно
                if client_dt.tzinfo is None:
                    client_dt = client_dt.replace(tzinfo=None)
                else:
                    client_dt = client_dt.replace(tzinfo=None)
                
                server_dt = metadata.last_updated
                if server_dt.tzinfo:
                    server_dt = server_dt.replace(tzinfo=None)
                
                has_updates = server_dt > client_dt
            except (ValueError, AttributeError) as e:
                # Если не удалось распарсить timestamp, считаем что есть обновления
                has_updates = True
        
        return success_response(data={
            'last_updated': format_datetime(metadata.last_updated),
            'has_updates': has_updates
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка проверки обновлений: {e}")
        return internal_error_response(f'Ошибка проверки обновлений: {str(e)}')


@bp.route('/data', methods=['GET'])
def get_all_data() -> Tuple[Dict[str, Any], int]:
    """
    Получение всех данных для синхронизации
    ---
    tags:
      - Синхронизация
    responses:
      200:
        description: Все данные для синхронизации
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                categories:
                  type: array
                  items:
                    type: object
                signs:
                  type: array
                  items:
                    type: object
                last_updated:
                  type: string
                  example: "2025-01-15T10:30:00Z"
    """
    try:
        categories = Category.query.order_by(Category.order).all()
        
        signs = Sign.query.options(
            joinedload(Sign.videos)
        ).order_by(func.lower(Sign.word)).all()
        
        sorted_signs = sort_signs_russian(signs)
        
        # Валидация данных
        signs_without_videos = [s for s in sorted_signs if not s.videos]
        if signs_without_videos:
            current_app.logger.warning(
                f"Найдено {len(signs_without_videos)} жестов без видео: "
                f"{[s.id for s in signs_without_videos[:5]]}"
            )
        
        # Получение метаданных
        metadata = SyncMetadata.query.first()
        if not metadata:
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        return success_response(data={
            'categories': [cat.to_dict() for cat in categories],
            'signs': [sign.to_dict_with_relations() for sign in sorted_signs],
            'last_updated': format_datetime(metadata.last_updated)
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка получения данных: {e}")
        return internal_error_response(f'Ошибка получения данных: {str(e)}')


@bp.route('/embeddings', methods=['GET'])
def get_embeddings() -> Tuple[Dict[str, Any], int]:
    """
    Получение embeddings всех жестов
    ---
    tags:
      - Синхронизация
    responses:
      200:
        description: Embeddings всех жестов
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                embeddings:
                  type: object
                  additionalProperties:
                    type: array
                    items:
                      type: number
                  example:
                    sign_001: [0.1, 0.2, 0.3]
                    sign_002: [0.4, 0.5, 0.6]
    """
    try:
        signs = Sign.query.filter(Sign.embeddings.isnot(None)).order_by(func.lower(Sign.word)).all()
        sorted_signs = sort_signs_russian(signs)
        
        embeddings_dict = {}
        for sign in sorted_signs:
            if sign.embeddings:
                embeddings_dict[sign.id] = sign.embeddings
        
        return success_response(data={'embeddings': embeddings_dict})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка получения embeddings: {e}")
        return internal_error_response(f'Ошибка получения embeddings: {str(e)}')


# =============================================================================
# RAW ENDPOINTS - Упрощенные эндпоинты для мобильных клиентов
# Возвращают данные без обертки {success, data, message}
# Даты в формате Unix timestamp (секунды)
# =============================================================================


def _build_sign_raw_response(sign: Sign) -> SignRawResponse:
    """
    Строит SignRawResponse из модели Sign с видео и синонимами.
    
    Args:
        sign: Объект Sign из БД
        
    Returns:
        SignRawResponse с видео и синонимами
    """
    # Получаем синонимы
    synonyms_query = SignSynonym.query.filter(
        (SignSynonym.sign_id_1 == sign.id) | (SignSynonym.sign_id_2 == sign.id)
    ).all()
    
    seen_ids = set()
    synonyms: List[SynonymRawResponse] = []
    for synonym in synonyms_query:
        other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == sign.id else synonym.sign_id_1
        if other_sign_id in seen_ids:
            continue
        seen_ids.add(other_sign_id)
        
        other_sign = Sign.query.get(other_sign_id)
        if other_sign:
            synonyms.append(SynonymRawResponse(id=other_sign.id, word=other_sign.word))
    
    # Строим видео с гарантированным context_description
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
    # Логируем использование raw endpoint для аналитики миграции
    current_app.logger.info("Raw endpoint accessed: /check/raw")
    
    client_timestamp_str = request.args.get('last_updated')
    metadata = SyncMetadata.query.first()
    
    if not metadata:
        # Если метаданных нет, создаём их
        metadata = SyncMetadata(last_updated=datetime.utcnow())
        db.session.add(metadata)
        db.session.commit()
    
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
    
    return jsonify(response.model_dump()), 200


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
            last_updated:
              type: integer
              description: Unix timestamp последнего обновления
              example: 1705318245
      500:
        description: Внутренняя ошибка сервера
    """
    # Логируем использование raw endpoint для аналитики миграции
    current_app.logger.info("Raw endpoint accessed: /data/raw")
    
    # Получаем категории
    categories = Category.query.order_by(Category.order).all()
    
    # Получаем жесты с видео
    signs = Sign.query.options(
        joinedload(Sign.videos)
    ).order_by(func.lower(Sign.word)).all()
    
    sorted_signs = sort_signs_russian(signs)
    
    # Валидация данных
    signs_without_videos = [s for s in sorted_signs if not s.videos]
    if signs_without_videos:
        current_app.logger.warning(
            f"Найдено {len(signs_without_videos)} жестов без видео: "
            f"{[s.id for s in signs_without_videos[:5]]}"
        )
    
    # Получение метаданных
    metadata = SyncMetadata.query.first()
    if not metadata:
        metadata = SyncMetadata(last_updated=datetime.utcnow())
        db.session.add(metadata)
        db.session.commit()
    
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
    
    response = SyncDataRawResponse(
        categories=categories_response,
        signs=signs_response,
        last_updated=metadata.last_updated
    )
    
    return jsonify(response.model_dump()), 200


@bp.route('/embeddings/raw', methods=['GET'])
@raw_error_handler
def get_embeddings_raw() -> Tuple[Dict[str, Any], int]:
    """
    Получение embeddings всех жестов (упрощенный формат без обертки)
    ---
    tags:
      - Синхронизация (Raw)
    responses:
      200:
        description: Embeddings всех жестов
        schema:
          type: object
          properties:
            embeddings:
              type: object
              additionalProperties:
                type: array
                items:
                  type: number
              example:
                sign_001: [0.1, 0.2, 0.3]
                sign_002: [0.4, 0.5, 0.6]
      500:
        description: Внутренняя ошибка сервера
    """
    # Логируем использование raw endpoint для аналитики миграции
    current_app.logger.info("Raw endpoint accessed: /embeddings/raw")
    
    signs = Sign.query.filter(Sign.embeddings.isnot(None)).order_by(func.lower(Sign.word)).all()
    sorted_signs = sort_signs_russian(signs)
    
    embeddings_dict = {}
    for sign in sorted_signs:
        if sign.embeddings:
            embeddings_dict[sign.id] = sign.embeddings
    
    return jsonify({"embeddings": embeddings_dict}), 200


# =============================================================================
# ПРАКТИЧЕСКАЯ РАБОТА №4 - ЗАКОММЕНТИРОВАНО
# Тестовые эндпоинты для генерации ошибок
# =============================================================================

# @bp.route('/test/error500', methods=['GET', 'POST'])
# def test_error_500() -> Tuple[Dict[str, Any], int]:
#     """
#     Тестовый эндпоинт для генерации 500 ошибки.
#     Используется для демонстрации логирования ERROR уровня.
#     ---
#     tags:
#       - Синхронизация
#     responses:
#       500:
#         description: Имитация внутренней ошибки сервера
#     """
#     current_app.logger.error("Тестовая ошибка 500: Имитация сбоя сервера")
#     return {'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': 'Тестовая ошибка сервера (500)'}}, 500
# 
# 
# @bp.route('/test/error503', methods=['GET', 'POST'])
# def test_error_503() -> Tuple[Dict[str, Any], int]:
#     """
#     Тестовый эндпоинт для генерации 503 ошибки (сервис недоступен).
#     ---
#     tags:
#       - Синхронизация
#     responses:
#       503:
#         description: Имитация недоступности сервиса
#     """
#     current_app.logger.error("Тестовая ошибка 503: Сервис временно недоступен")
#     return {'success': False, 'error': {'code': 'SERVICE_UNAVAILABLE', 'message': 'Сервис временно недоступен (503)'}}, 503
# 
# 
# @bp.route('/test/crash', methods=['GET', 'POST'])
# def test_crash() -> Tuple[Dict[str, Any], int]:
#     """
#     Тестовый эндпоинт для генерации необработанного исключения.
#     ---
#     tags:
#       - Синхронизация
#     responses:
#       500:
#         description: Необработанное исключение
#     """
#     raise RuntimeError("Тестовое необработанное исключение для демонстрации ERROR лога")

