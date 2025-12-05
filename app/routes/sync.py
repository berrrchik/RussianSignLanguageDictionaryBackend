"""
Endpoints для синхронизации мобильного приложения.
"""
from datetime import datetime
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sync_metadata import SyncMetadata
from app.utils.responses import success_response, internal_error_response
from app.utils.sorting import sort_signs_russian
from app.utils.formatters import format_datetime

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

