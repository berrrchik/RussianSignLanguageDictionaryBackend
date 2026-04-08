"""
Endpoints для управления жестами.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app
from sqlalchemy import func

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.validators import validate_sign_data, validate_entity_exists
from app.utils.decorators import handle_db_errors, require_json
from app.utils.responses import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response
)
from app.utils.sorting import sort_signs_russian
from app.constants import DEFAULT_PAGE, DEFAULT_PER_PAGE
from app.utils.metrics import admin_sign_operations
from app.utils.logging_config import get_logger, log_business_event

bp = Blueprint('admin_signs', __name__)
logger = get_logger(__name__)


@bp.route('/signs', methods=['GET'])
@require_auth
@handle_db_errors('получения списка жестов')
def list_signs() -> Tuple[Dict[str, Any], int]:
    """
    Получение списка жестов с пагинацией
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Номер страницы
      - name: per_page
        in: query
        type: integer
        default: 50
        description: Количество на странице
      - name: category_id
        in: query
        type: string
        required: false
        description: Фильтр по категории
      - name: search
        in: query
        type: string
        required: false
        description: Поиск по слову или ID
    responses:
      200:
        description: Список жестов
      401:
        description: Неавторизован
    """
    page = request.args.get('page', DEFAULT_PAGE, type=int)
    per_page = request.args.get('per_page', DEFAULT_PER_PAGE, type=int)
    category_id = request.args.get('category_id')
    search = request.args.get('search', '').strip()
    
    # Построение запроса
    query = Sign.query.order_by(func.lower(Sign.word))
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            (Sign.word.ilike(search_pattern)) |
            (Sign.id.ilike(search_pattern))
        )
    
    # Получение всех жестов и сортировка
    all_signs = query.all()
    sorted_signs = sort_signs_russian(all_signs)
    
    # Пагинация
    total = len(sorted_signs)
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = sorted_signs[start_idx:end_idx]
    
    return success_response(data={
            'signs': [sign.to_dict() for sign in paginated_items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages
            }
        })


@bp.route('/signs/<sign_id>', methods=['GET'])
@require_auth
@handle_db_errors('получения жеста')
def get_sign(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение жеста по ID
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
        description: ID жеста
    responses:
      200:
        description: Данные жеста
      404:
        description: Жест не найден
    """
    sign = Sign.query.get_or_404(sign_id)
    return success_response(data=sign.to_dict_with_relations())


@bp.route('/signs', methods=['POST'])
@require_auth
@require_json
@handle_db_errors('создания жеста')
def create_sign() -> Tuple[Dict[str, Any], int]:
    """
    Создание нового жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - id
            - word
            - category_id
          properties:
            id:
              type: string
              example: "sign_001"
            word:
              type: string
              example: "привет"
            description:
              type: string
              example: "Приветствие"
            category_id:
              type: string
              example: "greetings"
    responses:
      201:
        description: Жест создан
      400:
        description: Ошибка валидации
    """
    data = request.get_json()
    
    # Валидация
    errors = validate_sign_data(data)
    if errors:
        return validation_error_response(errors)
    
    # Проверка существования категории
    category, error = validate_entity_exists(Category, data['category_id'], 'Категория')
    if error:
        return error
    
    # Проверка уникальности ID
    if Sign.query.get(data.get('id')):
        return error_response('DUPLICATE_ID', 'Жест с таким ID уже существует', 400)
    
    # Создание жеста
    sign = Sign(
        id=data['id'],
        word=data['word'],
        description=data.get('description'),
        category_id=data['category_id']
    )
    db.session.add(sign)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_sign_operations.labels(operation='create').inc()
    
    log_business_event(logger, "Sign created", {
        "sign_id": sign.id,
        "word": sign.word,
        "category_id": sign.category_id
    }, event_domain="admin_content", event_name="sign_created", resource="sign", action="create", outcome="success")
    
    return success_response(data=sign.to_dict(), status_code=201)


@bp.route('/signs/<sign_id>', methods=['PUT'])
@require_auth
@require_json
@handle_db_errors('обновления жеста')
def update_sign(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Обновление жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            word:
              type: string
              example: "привет"
            description:
              type: string
              example: "Приветствие"
            category_id:
              type: string
              example: "greetings"
    responses:
      200:
        description: Жест обновлён
      404:
        description: Жест не найден
    """
    sign = Sign.query.get_or_404(sign_id)
    data = request.get_json()
    
    # Валидация
    errors = validate_sign_data(data)
    if errors:
        return validation_error_response(errors)
    
    # Обновление полей
    if 'word' in data:
        sign.word = data['word']
    if 'description' in data:
        sign.description = data.get('description')
    if 'category_id' in data:
        category, error = validate_entity_exists(Category, data['category_id'], 'Категория')
        if error:
            return error
        sign.category_id = data['category_id']
    
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_sign_operations.labels(operation='update').inc()
    
    log_business_event(logger, "Sign updated", {
        "sign_id": sign_id
    }, event_domain="admin_content", event_name="sign_updated", resource="sign", action="update", outcome="success")
    
    return success_response(data=sign.to_dict())


@bp.route('/signs/<sign_id>', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления жеста')
def delete_sign(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Удаление жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Жест удалён
      404:
        description: Жест не найден
    """
    sign = Sign.query.get_or_404(sign_id)
    
    videos = SignVideo.query.filter_by(sign_id=sign_id).all()
    if videos:
        try:
            from app.utils.storage import get_video_storage
            storage = get_video_storage()
            
            for video in videos:
                if not storage.delete(video.file_path):
                    current_app.logger.warning(f"Не удалось удалить файл {video.file_path} из хранилища")
        except Exception as e:
            current_app.logger.warning(f"Ошибка при удалении видео из хранилища: {e}")
    
    db.session.delete(sign)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    # Добавляем метрику и логирование
    admin_sign_operations.labels(operation='delete').inc()
    
    log_business_event(logger, "Sign deleted", {
        "sign_id": sign_id
    }, event_domain="admin_content", event_name="sign_deleted", resource="sign", action="delete", outcome="success")
    
    return success_response(message='Жест удалён')

