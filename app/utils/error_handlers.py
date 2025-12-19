"""
Утилиты для обработки ошибок в /raw эндпоинтах.

Эти декораторы предоставляют упрощенную обработку ошибок без обертки
{success, error} для оптимизированных мобильных эндпоинтов.
"""
from functools import wraps
from typing import Callable, Any
from flask import jsonify, current_app


class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    pass


class NotFoundError(Exception):
    """Исключение для ресурсов не найденных."""
    pass


class AuthorizationError(Exception):
    """Исключение для ошибок авторизации."""
    pass


def raw_error_handler(f: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в /raw эндпоинтах.
    
    Возвращает структуру {error: str, message: str} с соответствующими
    HTTP статус кодами вместо обертки {success, error}.
    
    Обрабатывает:
        - ValidationError, ValueError -> 400 Bad Request
        - NotFoundError -> 404 Not Found
        - AuthorizationError -> 403 Forbidden
        - Exception -> 500 Internal Server Error
    
    Example:
        @bp.route('/data/raw', methods=['GET'])
        @raw_error_handler
        def get_sync_data_raw():
            # ... логика эндпоинта
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            current_app.logger.warning(f"Validation error in {f.__name__}: {e}")
            return jsonify({
                "error": "ValidationError",
                "message": str(e)
            }), 400
        except ValueError as e:
            current_app.logger.warning(f"Value error in {f.__name__}: {e}")
            return jsonify({
                "error": "ValidationError",
                "message": str(e)
            }), 400
        except NotFoundError as e:
            current_app.logger.warning(f"Not found in {f.__name__}: {e}")
            return jsonify({
                "error": "NotFoundError",
                "message": str(e)
            }), 404
        except AuthorizationError as e:
            current_app.logger.warning(f"Authorization error in {f.__name__}: {e}")
            return jsonify({
                "error": "AuthorizationError",
                "message": str(e)
            }), 403
        except Exception as e:
            current_app.logger.error(f"Internal error in {f.__name__}: {e}", exc_info=True)
            return jsonify({
                "error": "InternalServerError",
                "message": "An unexpected error occurred"
            }), 500
    return decorated_function
