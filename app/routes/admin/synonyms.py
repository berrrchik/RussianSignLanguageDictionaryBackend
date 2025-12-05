"""
Endpoints для управления синонимами жестов.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app

from app.database import db
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.responses import (
    success_response,
    error_response,
    not_found_response,
    internal_error_response
)

bp = Blueprint('admin_synonyms', __name__)


@bp.route('/signs/<sign_id>/synonyms', methods=['GET'])
@require_auth
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
    try:
        sign = Sign.query.get_or_404(sign_id)
        
        # Получение всех связей синонимов
        synonyms_query = SignSynonym.query.filter(
            (SignSynonym.sign_id_1 == sign_id) | (SignSynonym.sign_id_2 == sign_id)
        ).all()
        
        synonyms = []
        for synonym in synonyms_query:
            other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == sign_id else synonym.sign_id_1
            other_sign = Sign.query.get(other_sign_id)
            if other_sign:
                synonyms.append({
                    'id': other_sign.id,
                    'word': other_sign.word
                })
        
        return success_response(data=synonyms)
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка синонимов: {e}")
        return internal_error_response('Ошибка получения списка синонимов')


@bp.route('/signs/<sign_id>/synonyms', methods=['POST'])
@require_auth
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
    try:
        sign = Sign.query.get_or_404(sign_id)
        data = request.get_json()
        
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        
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
        existing = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == sign_id) & (SignSynonym.sign_id_2 == synonym_id)) |
            ((SignSynonym.sign_id_1 == synonym_id) & (SignSynonym.sign_id_2 == sign_id))
        ).first()
        
        if existing:
            return error_response('SYNONYM_EXISTS', 'Связь синонимов уже существует', 400)
        
        # Создание двусторонней связи
        synonym1 = SignSynonym(sign_id_1=sign_id, sign_id_2=synonym_id)
        synonym2 = SignSynonym(sign_id_1=synonym_id, sign_id_2=sign_id)
        
        db.session.add(synonym1)
        db.session.add(synonym2)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(message='Синоним добавлен', status_code=201)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка добавления синонима: {e}")
        return internal_error_response('Ошибка добавления синонима')


@bp.route('/signs/<sign_id>/synonyms/<synonym_id>', methods=['DELETE'])
@require_auth
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
    try:
        # Удаление обеих связей (двусторонних)
        synonyms = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == sign_id) & (SignSynonym.sign_id_2 == synonym_id)) |
            ((SignSynonym.sign_id_1 == synonym_id) & (SignSynonym.sign_id_2 == sign_id))
        ).all()
        
        if not synonyms:
            return error_response('SYNONYM_NOT_FOUND', 'Связь синонимов не найдена', 404)
        
        for synonym in synonyms:
            db.session.delete(synonym)
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(message='Связь синонимов удалена')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления синонима: {e}")
        return internal_error_response('Ошибка удаления синонима')


@bp.route('/synonyms/<int:synonym_id>', methods=['DELETE'])
@require_auth
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
    try:
        synonym = SignSynonym.query.get_or_404(synonym_id)
        
        # Удаление обеих связей (двусторонних)
        synonyms = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == synonym.sign_id_1) & (SignSynonym.sign_id_2 == synonym.sign_id_2)) |
            ((SignSynonym.sign_id_1 == synonym.sign_id_2) & (SignSynonym.sign_id_2 == synonym.sign_id_1))
        ).all()
        
        for syn in synonyms:
            db.session.delete(syn)
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(message='Связь синонимов удалена')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления синонима: {e}")
        return internal_error_response('Ошибка удаления синонима')

