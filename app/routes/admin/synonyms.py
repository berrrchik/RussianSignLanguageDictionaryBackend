"""
Endpoints для управления синонимами жестов.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request

from app.database import db
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.constants import DEFAULT_PAGE, DEFAULT_PER_PAGE, MAX_PER_PAGE
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


@bp.route('/synonyms', methods=['GET'])
@require_auth
@handle_db_errors('получения списка связей синонимов')
def list_all_synonyms() -> Tuple[Dict[str, Any], int]:
    """
    Получение списка связей синонимов (глобально)
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 50
      - name: search
        in: query
        type: string
        required: false
        description: Поиск по id/слову обоих жестов
    responses:
      200:
        description: Список связей синонимов
    """
    page = request.args.get('page', DEFAULT_PAGE, type=int)
    per_page = request.args.get('per_page', DEFAULT_PER_PAGE, type=int)
    per_page = min(max(1, per_page), MAX_PER_PAGE)
    search = (request.args.get('search', '') or '').strip()

    # Загружаем все связи и сводим к уникальным парам (учитывая двусторонние записи)
    relations = SignSynonym.query.order_by(SignSynonym.id.asc()).all()
    unique_by_pair: Dict[tuple, SignSynonym] = {}
    for rel in relations:
        a, b = rel.sign_id_1, rel.sign_id_2
        key = (a, b) if a <= b else (b, a)
        if key not in unique_by_pair:
            unique_by_pair[key] = rel

    unique_relations = list(unique_by_pair.values())

    # Подтягиваем слова жестов одним запросом
    sign_ids = set()
    for rel in unique_relations:
        sign_ids.add(rel.sign_id_1)
        sign_ids.add(rel.sign_id_2)
    signs = Sign.query.filter(Sign.id.in_(list(sign_ids))).all() if sign_ids else []
    sign_word_by_id = {s.id: s.word for s in signs}

    # Формируем DTO
    items = []
    for rel in unique_relations:
        sign_1_id = rel.sign_id_1
        sign_2_id = rel.sign_id_2
        items.append({
            "id": rel.id,
            "sign_1_id": sign_1_id,
            "sign_1_word": sign_word_by_id.get(sign_1_id),
            "sign_2_id": sign_2_id,
            "sign_2_word": sign_word_by_id.get(sign_2_id),
            "created_at": rel.to_dict().get("created_at"),
        })

    # Поиск (по id или слову любого из жестов)
    if search:
        search_lower = search.lower()
        def match(item: Dict[str, Any]) -> bool:
            return (
                (item.get("sign_1_id") or "").lower().find(search_lower) != -1 or
                (item.get("sign_2_id") or "").lower().find(search_lower) != -1 or
                (item.get("sign_1_word") or "").lower().find(search_lower) != -1 or
                (item.get("sign_2_word") or "").lower().find(search_lower) != -1 or
                str(item.get("id", "")).find(search) != -1
            )
        items = [it for it in items if match(it)]

    # Стабильная сортировка: по словам, затем по id
    items.sort(key=lambda x: (
        (x.get("sign_1_word") or ""),
        (x.get("sign_2_word") or ""),
        x.get("id", 0),
    ))

    total = len(items)
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    page = max(1, min(page, pages))
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = items[start_idx:end_idx]

    return success_response(data={
        "synonyms": paginated,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
    })


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
