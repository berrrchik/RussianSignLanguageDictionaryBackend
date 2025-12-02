"""
Endpoints для синхронизации мобильного приложения.
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sync_metadata import SyncMetadata

bp = Blueprint('sync', __name__)


@bp.route('/check', methods=['GET'])
def check_updates():
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
        
        return jsonify({
            'success': True,
            'data': {
                'last_updated': metadata.last_updated.isoformat() + 'Z',
                'has_updates': has_updates
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'Ошибка проверки обновлений: {str(e)}'
            }
        }), 500


@bp.route('/data', methods=['GET'])
def get_all_data():
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
        # Загрузка категорий
        categories = Category.query.order_by(Category.order).all()
        
        # Загрузка жестов с видео и синонимами (eager loading)
        signs = Sign.query.options(
            joinedload(Sign.videos)
        ).all()
        
        # Получение метаданных
        metadata = SyncMetadata.query.first()
        if not metadata:
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'categories': [cat.to_dict() for cat in categories],
                'signs': [sign.to_dict_with_relations() for sign in signs],
                'last_updated': metadata.last_updated.isoformat() + 'Z'
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': f'Ошибка получения данных: {str(e)}'
            }
        }), 500

