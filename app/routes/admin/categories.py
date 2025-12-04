"""
Endpoints для управления категориями.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app
from sqlalchemy import func

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.validators import validate_category_data
from app.utils.responses import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    internal_error_response
)
from app.utils.sorting import sort_signs_russian

bp = Blueprint('admin_categories', __name__)


@bp.route('/categories', methods=['GET'])
@require_auth
def list_categories() -> Tuple[Dict[str, Any], int]:
    """
    Получение списка категорий.
    
    Returns:
        JSON ответ со списком категорий
    """
    try:
        categories = Category.query.order_by(Category.order).all()
        return success_response(data=[cat.to_dict() for cat in categories])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка категорий: {e}")
        return internal_error_response('Ошибка получения списка категорий')


@bp.route('/categories/<category_id>', methods=['GET'])
@require_auth
def get_category(category_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение категории по ID.
    
    Args:
        category_id: ID категории
        
    Returns:
        JSON ответ с данными категории
    """
    try:
        category = Category.query.get_or_404(category_id)
        return success_response(data=category.to_dict())
    except Exception as e:
        current_app.logger.error(f"Ошибка получения категории: {e}")
        return not_found_response('Категория')


@bp.route('/categories', methods=['POST'])
@require_auth
def create_category() -> Tuple[Dict[str, Any], int]:
    """
    Создание новой категории.
    
    Returns:
        JSON ответ с созданной категорией
    """
    try:
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        
        # Валидация
        errors = validate_category_data(data)
        if errors:
            return validation_error_response(errors)
        
        # Проверка уникальности ID
        if Category.query.get(data.get('id')):
            return error_response('DUPLICATE_ID', 'Категория с таким ID уже существует', 400)
        
        category = Category(
            id=data['id'],
            name=data['name'],
            order=data.get('order', 0)
        )
        db.session.add(category)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(data=category.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка создания категории: {e}")
        return internal_error_response('Ошибка создания категории')


@bp.route('/categories/<category_id>', methods=['PUT'])
@require_auth
def update_category(category_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Обновление категории.
    
    Args:
        category_id: ID категории
        
    Returns:
        JSON ответ с обновленной категорией
    """
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        
        # Валидация
        errors = validate_category_data(data)
        if errors:
            return validation_error_response(errors)
        
        if 'name' in data:
            category.name = data['name']
        if 'order' in data:
            category.order = data['order']
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(data=category.to_dict())
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления категории: {e}")
        return internal_error_response('Ошибка обновления категории')


@bp.route('/categories/<category_id>', methods=['DELETE'])
@require_auth
def delete_category(category_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Удаление категории.
    
    Args:
        category_id: ID категории
        
    Returns:
        JSON ответ об успешном удалении
    """
    try:
        category = Category.query.get_or_404(category_id)
        
        # Проверка наличия жестов в категории
        signs_count = Sign.query.filter_by(category_id=category_id).count()
        if signs_count > 0:
            return error_response(
                'CATEGORY_HAS_SIGNS',
                f'Невозможно удалить категорию: в ней содержится {signs_count} жестов',
                400
            )
        
        db.session.delete(category)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(message='Категория удалена')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления категории: {e}")
        return internal_error_response('Ошибка удаления категории')


@bp.route('/categories/<category_id>/signs', methods=['GET'])
@require_auth
def get_category_signs(category_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение жестов категории.
    
    Args:
        category_id: ID категории
        
    Returns:
        JSON ответ со списком жестов категории
    """
    try:
        category = Category.query.get_or_404(category_id)
        signs = Sign.query.filter_by(category_id=category_id).order_by(func.lower(Sign.word)).all()
        
        sorted_signs = sort_signs_russian(signs)
        
        return success_response(data=[sign.to_dict() for sign in sorted_signs])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения жестов категории: {e}")
        return internal_error_response('Ошибка получения жестов категории')

