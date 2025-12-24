"""
Endpoints для управления синонимами жестов.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request

from app.database import db
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.decorators import handle_db_errors, require_json
from app.utils.synonyms import (
    get_sign_synonyms,
    delete_synonym_relation,
    check_synonym_exists,
    create_synonym_relation
)
from app.utils.responses import (
    success_response,
    error_response,
    not_found_response
)

bp = Blueprint('admin_synonyms', __name__)


@bp.route('/signs/<sign_id>/synonyms', methods=['GET'])
@require_auth
@handle_db_errors('получения списка синонимов')
def list_synonyms(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение списка синонимов для жеста
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Список синонимов
      404:
        description: Жест не найден
    """
    Sign.query.get_or_404(sign_id)
    synonyms = get_sign_synonyms(sign_id)
    return success_response(data=synonyms)


@bp.route('/signs/<sign_id>/synonyms', methods=['POST'])
@require_auth
@require_json
@handle_db_errors('добавления синонима')
def add_synonym(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Добавление синонима для жеста
    ---
    tags:
      - Синонимы
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
          required:
            - synonym_sign_id
          properties:
            synonym_sign_id:
              type: string
              example: "sign_002"
    responses:
      201:
        description: Синоним добавлен
      400:
        description: Ошибка валидации
      404:
        description: Жест не найден
    """
    Sign.query.get_or_404(sign_id)
    data = request.get_json()
    
    synonym_id = data.get('synonym_sign_id')
    if not synonym_id:
        return error_response('MISSING_FIELD', 'Требуется поле synonym_sign_id', 400)
    
    # Проверка существования жеста-синонима
    synonym_sign = Sign.query.get(synonym_id)
    if not synonym_sign:
        return not_found_response('Жест-синоним')
    
    if sign_id == synonym_id:
        return error_response('INVALID_SYNONYM', 'Жест не может быть синонимом самому себе', 400)
    
    # Проверка существования связи
    if check_synonym_exists(sign_id, synonym_id):
        return error_response('SYNONYM_EXISTS', 'Связь синонимов уже существует', 400)
    
    # Создание двусторонней связи
    create_synonym_relation(sign_id, synonym_id)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    return success_response(message='Синоним добавлен', status_code=201)


@bp.route('/signs/<sign_id>/synonyms/<synonym_id>', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления синонима')
def delete_synonym(sign_id: str, synonym_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Удаление связи синонимов
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: synonym_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Связь синонимов удалена
      404:
        description: Связь не найдена
    """
    if not delete_synonym_relation(sign_id, synonym_id):
        return error_response('SYNONYM_NOT_FOUND', 'Связь синонимов не найдена', 404)
    
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    return success_response(message='Связь синонимов удалена')


@bp.route('/synonyms/<int:synonym_id>', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления синонима')
def delete_synonym_by_id(synonym_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Удаление связи синонимов по ID связи
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: synonym_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Связь синонимов удалена
      404:
        description: Связь не найдена
    """
    synonym = SignSynonym.query.get_or_404(synonym_id)
    
    # Удаление обеих связей (двусторонних)
    delete_synonym_relation(synonym.sign_id_1, synonym.sign_id_2)
    db.session.commit()
    
    # Обновление метаданных синхронизации
    update_sync_metadata()
    
    return success_response(message='Связь синонимов удалена')
