"""
Endpoints для авторизации администратора.
"""
from datetime import datetime
from typing import Tuple, Dict, Any
from flask import Blueprint, request, jsonify, current_app
import bcrypt

from app.database import db
from app.models.admin_user import AdminUser
from app.utils.auth import generate_token
from app.utils.responses import error_response, success_response

bp = Blueprint('admin_auth', __name__)


@bp.route('/auth/login', methods=['POST'])
def login() -> Tuple[Dict[str, Any], int]:
    """
    Авторизация администратора.
    
    Returns:
        JSON ответ с токеном или ошибкой
    """
    try:
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return error_response('MISSING_CREDENTIALS', 'Требуются username и password', 400)
        
        user = AdminUser.query.filter_by(username=username).first()
        
        if user and bcrypt.checkpw(
            password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        ):
            # Обновление last_login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Генерация токена
            token = generate_token(
                user.id,
                current_app.config['JWT_SECRET_KEY'],
                current_app.config['JWT_EXPIRATION_DELTA']
            )
            
            return success_response(
                data={
                    'token': token,
                    'expires_in': current_app.config['JWT_EXPIRATION_DELTA']
                }
            )
        
        return error_response('INVALID_CREDENTIALS', 'Неверный username или password', 401)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка авторизации: {e}")
        return error_response('INTERNAL_ERROR', 'Ошибка авторизации', 500)

