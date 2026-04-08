"""
Декораторы для Flask эндпоинтов.

Содержит универсальные декораторы для:
- Обработки ошибок БД
- Валидации JSON body
"""
from functools import wraps
from typing import Callable, Optional

from flask import request, current_app

from app.database import db
from app.utils.responses import error_response, internal_error_response


def handle_db_errors(operation_name: Optional[str] = None):
    """
    Декоратор для обработки ошибок БД в эндпоинтах.
    
    Автоматически делает rollback при ошибках и возвращает
    стандартизированный ответ об ошибке.
    
    Args:
        operation_name: Название операции для логирования.
                       Если не указано, используется имя функции.
    
    Example:
        @bp.route('/signs', methods=['POST'])
        @require_auth
        @handle_db_errors('создания жеста')
        def create_sign():
            # логика без try/except
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                db.session.rollback()
                op_name = operation_name or f.__name__
                current_app.logger.error(
                    f"Ошибка {op_name}: {e}",
                    exc_info=True,
                    extra={
                        "event_kind": "application",
                        "event_domain": "application",
                        "event_name": "database_operation_failed",
                        "outcome": "failure",
                        "extra_data": {"operation": op_name},
                    },
                )
                return internal_error_response(f'Ошибка {op_name}')
        return decorated_function
    return decorator


def require_json(f: Callable) -> Callable:
    """
    Декоратор для проверки наличия JSON body в запросе.
    
    Возвращает ошибку 400, если JSON body отсутствует или пустой.
    
    Example:
        @bp.route('/signs', methods=['POST'])
        @require_auth
        @require_json
        def create_sign():
            data = request.get_json()  # уже проверено
            # остальная логика
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        return f(*args, **kwargs)
    return decorated_function
