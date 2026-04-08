"""
Утилиты для авторизации и JWT токенов.
"""
from typing import Callable, Any
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask import current_app, g, request
from app.models.admin_user import AdminUser
from app.utils.responses import error_response


def generate_token(user_id: int, secret_key: str, expiration_delta: int) -> str:
    """
    Генерация JWT токена.
    
    Args:
        user_id: ID пользователя
        secret_key: Секретный ключ для подписи
        expiration_delta: Время жизни токена в секундах
        
    Returns:
        JWT токен
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expiration_delta),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_token(token: str, secret_key: str) -> dict:
    """
    Проверка JWT токена.
    
    Args:
        token: JWT токен
        secret_key: Секретный ключ для проверки
        
    Returns:
        Payload токена
        
    Raises:
        jwt.ExpiredSignatureError: Токен истёк
        jwt.InvalidTokenError: Невалидный токен
    """
    return jwt.decode(token, secret_key, algorithms=['HS256'])


def require_auth(f: Callable) -> Callable:
    """
    Декоратор для защиты endpoints авторизацией.
    
    Проверяет JWT токен из заголовка Authorization: Bearer <token>
    
    Args:
        f: Функция для декорирования
        
    Returns:
        Декорированная функция
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        token = None
        
        # Получение токена из заголовка
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return error_response('INVALID_TOKEN_FORMAT', 'Неверный формат токена. Используйте: Bearer <token>', 401)
        
        if not token:
            return error_response('TOKEN_REQUIRED', 'Требуется токен авторизации', 401)
        
        try:
            # Проверка токена
            payload = verify_token(token, current_app.config['JWT_SECRET_KEY'])
            user_id = payload['user_id']
            
            # Проверка существования пользователя
            user = AdminUser.query.get(user_id)
            if not user:
                return error_response('USER_NOT_FOUND', 'Пользователь не найден', 401)
            
            # Добавление пользователя в контекст запроса и логи
            request.current_user = user
            g.user_id = user.id
            g.username = user.username
            
        except jwt.ExpiredSignatureError:
            return error_response('TOKEN_EXPIRED', 'Токен истёк', 401)
        except jwt.InvalidTokenError:
            return error_response('INVALID_TOKEN', 'Невалидный токен', 401)
        
        return f(*args, **kwargs)
    
    return decorated_function
