"""
Endpoints для поиска жестов.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app

from app.services.sbert_search_service import get_sbert_search_service
from app.utils.responses import success_response, error_response
from app.utils.decorators import handle_db_errors, require_json
from app.constants import MAX_DESCRIPTION_LENGTH


bp = Blueprint('search', __name__)


@bp.route('/sbert', methods=['POST'])
@require_json
@handle_db_errors('поиска похожих жестов через SBERT')
def search_sbert() -> Tuple[Dict[str, Any], int]:
    """
    Поиск похожих жестов по текстовому запросу с использованием SBERT модели
    ---
    tags:
      - Поиск
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - text
          properties:
            text:
              type: string
              example: "привет"
            limit:
              type: integer
              default: 10
              minimum: 1
              maximum: 50
              description: Максимальное количество результатов
            min_similarity:
              type: number
              default: 0.0
              minimum: 0.0
              maximum: 1.0
              description: Минимальное значение сходства (0-1)
            model_path:
              type: string
              default: "ai-forever/sbert_large_nlu_ru"
              description: Путь к модели SBERT (опционально)
    responses:
      200:
        description: Список похожих жестов
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                query:
                  type: string
                  example: "привет"
                results:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "sign_001"
                      word:
                        type: string
                        example: "привет"
                      similarity:
                        type: number
                        example: 0.95
      400:
        description: Ошибка валидации
      503:
        description: Модель недоступна
      500:
        description: Ошибка поиска
    """
    data = request.get_json()
    
    text = data.get('text', '').strip()
    if not text:
        return error_response('VALIDATION_ERROR', 'Поле text не может быть пустым', 400)
    
    if len(text) > MAX_DESCRIPTION_LENGTH:
        return error_response(
            'VALIDATION_ERROR',
            f'Текст не может быть длиннее {MAX_DESCRIPTION_LENGTH} символов',
            400
        )
    
    # Параметры поиска
    limit = data.get('limit', 10)
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        limit = 10
    
    min_similarity = data.get('min_similarity', 0.0)
    if not isinstance(min_similarity, (int, float)) or min_similarity < 0.0 or min_similarity > 1.0:
        min_similarity = 0.0
    
    # Путь к модели (опционально)
    model_path = data.get('model_path', 'ai-forever/sbert_large_nlu_ru')
    
    try:
        # Получение сервиса поиска
        search_service = get_sbert_search_service(model_path=model_path)
        
        # Поиск похожих жестов
        results = search_service.search(
            search_query=text,
            limit=limit,
            min_similarity=min_similarity
        )
        
        # Форматирование результатов
        formatted_results = [
            {
                'id': sign_id,
                'word': word,
                'similarity': round(similarity, 4)
            }
            for sign_id, word, similarity in results
        ]
        
        return success_response(data={
            'query': text,
            'results': formatted_results,
            'total_found': len(formatted_results),
            'model': model_path
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка SBERT поиска: {e}", exc_info=True)
        return error_response(
            'SEARCH_ERROR',
            f'Ошибка поиска: {str(e)}',
            500
        )
