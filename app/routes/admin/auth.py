"""
Endpoints для авторизации администратора.
"""
from datetime import datetime
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app
import bcrypt

from app.database import db
from app.models.admin_user import AdminUser
from app.utils.auth import generate_token
from app.utils.decorators import handle_db_errors, require_json
from app.utils.responses import error_response, success_response

bp = Blueprint('admin_auth', __name__)


@bp.route('/auth/login', methods=['POST'])
@require_json
@handle_db_errors('авторизации')
def login() -> Tuple[Dict[str, Any], int]:
    """
    Авторизация администратора
    ---
    tags:
      - Авторизация
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: admin
            password:
              type: string
              example: password
    responses:
      200:
        description: Успешная авторизация
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                token:
                  type: string
                  example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
                expires_in:
                  type: integer
                  example: 3600
      401:
        description: Неверные учетные данные
    """
    data = request.get_json()
    
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
