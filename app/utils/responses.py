"""
Утилиты для стандартизированных ответов API.
"""
from typing import Any, Dict, Optional, Tuple
from flask import jsonify

from app.constants import ERROR_CODES


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200
) -> Tuple[Dict[str, Any], int]:
    """
    Создание успешного ответа API.
    
    Args:
        data: Данные для ответа
        message: Опциональное сообщение
        status_code: HTTP статус код
        
    Returns:
        Tuple[dict, int]: JSON ответ и статус код
    """
    response = {'success': True}
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return jsonify(response), status_code


def error_response(
    error_code: str,
    message: str,
    status_code: int = 400
) -> Tuple[Dict[str, Any], int]:
    """
    Создание ответа об ошибке API.
    
    Args:
        error_code: Код ошибки из ERROR_CODES
        message: Сообщение об ошибке
        status_code: HTTP статус код
        
    Returns:
        Tuple[dict, int]: JSON ответ и статус код
    """
    return jsonify({
        'success': False,
        'error': {
            'code': ERROR_CODES.get(error_code, error_code),
            'message': message
        }
    }), status_code


def validation_error_response(errors: list) -> Tuple[Dict[str, Any], int]:
    """
    Создание ответа об ошибке валидации.
    
    Args:
        errors: Список строк с ошибками валидации
        
    Returns:
        Tuple[dict, int]: JSON ответ и статус код
    """
    return error_response(
        'VALIDATION_ERROR',
        '; '.join(errors),
        400
    )


def not_found_response(resource: str = 'Ресурс') -> Tuple[Dict[str, Any], int]:
    """
    Создание ответа "не найдено".
    
    Args:
        resource: Название ресурса
        
    Returns:
        Tuple[dict, int]: JSON ответ и статус код
    """
    return error_response(
        'NOT_FOUND',
        f'{resource} не найден',
        404
    )


def internal_error_response(message: str = 'Внутренняя ошибка сервера') -> Tuple[Dict[str, Any], int]:
    """
    Создание ответа о внутренней ошибке.
    
    Args:
        message: Сообщение об ошибке
        
    Returns:
        Tuple[dict, int]: JSON ответ и статус код
    """
    return error_response(
        'INTERNAL_ERROR',
        message,
        500
    )

