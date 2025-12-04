"""
Endpoints для поиска жестов.
"""
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app

from app.services.embeddings_service import EmbeddingsService
from app.utils.responses import success_response, error_response, internal_error_response
from app.constants import MAX_DESCRIPTION_LENGTH


bp = Blueprint('search', __name__)


@bp.route('/generate-embedding', methods=['POST'])
def generate_embedding() -> Tuple[Dict[str, Any], int]:
    """
    Генерация embeddings из текстового запроса
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
    responses:
      200:
        description: Сгенерированные embeddings
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                embedding:
                  type: array
                  items:
                    type: number
                  example: [0.1, 0.2, 0.3]
      400:
        description: Ошибка валидации
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: object
              properties:
                code:
                  type: string
                  example: "VALIDATION_ERROR"
                message:
                  type: string
                  example: "Поле text не может быть пустым"
      503:
        description: Модель недоступна
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: object
              properties:
                code:
                  type: string
                  example: "MODEL_NOT_AVAILABLE"
                message:
                  type: string
                  example: "Модель для генерации embeddings недоступна"
      500:
        description: Ошибка генерации
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: object
              properties:
                code:
                  type: string
                  example: "INTERNAL_ERROR"
                message:
                  type: string
                  example: "Ошибка генерации embeddings: ..."
    """
    try:
        data = request.get_json()
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON body', 400)
        
        text = data.get('text', '').strip()
        if not text:
            return error_response('VALIDATION_ERROR', 'Поле text не может быть пустым', 400)
        
        if len(text) > MAX_DESCRIPTION_LENGTH:
            return error_response(
                'VALIDATION_ERROR',
                f'Текст не может быть длиннее {MAX_DESCRIPTION_LENGTH} символов',
                400
            )
        
        if not EmbeddingsService.is_generator_available():
            return error_response('MODEL_NOT_AVAILABLE', 'Модель для генерации embeddings недоступна', 503)
        
        embedding = EmbeddingsService.generate_for_text(text)
        if not embedding:
            return error_response('GENERATION_FAILED', 'Не удалось сгенерировать embeddings', 500)
        
        return success_response(data={'embedding': embedding})
    except Exception as e:
        current_app.logger.error(f"Ошибка генерации embeddings: {e}")
        return internal_error_response(f'Ошибка генерации embeddings: {str(e)}')

