"""
Endpoints для управления видео.
"""
import os
from typing import Tuple, Dict, Any
from flask import Blueprint, request, current_app

from app.database import db
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.utils.auth import require_auth
from app.utils.sync import update_sync_metadata
from app.utils.validators import validate_video_data
from app.utils.storage import get_video_storage
from app.utils.decorators import handle_db_errors, require_json
from app.utils.responses import (
    success_response,
    error_response,
    validation_error_response
)
from app.constants import VIDEO_MAX_SIZE

bp = Blueprint('admin_videos', __name__)


@bp.route('/signs/<sign_id>/videos', methods=['GET'])
@require_auth
@handle_db_errors('получения списка видео')
def list_videos(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение списка видео для жеста
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: sign_id
    in: path
    type: string
    required: true
    responses:
      200:
    description: Список видео
      404:
    description: Жест не найден
    """
    Sign.query.get_or_404(sign_id)
    videos = SignVideo.query.filter_by(sign_id=sign_id).order_by(SignVideo.order).all()
    return success_response(data=[video.to_dict() for video in videos])


@bp.route('/signs/<sign_id>/videos', methods=['POST'])
@require_auth
@handle_db_errors('загрузки видео')
def upload_video(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Загрузка видео для жеста
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: sign_id
    in: path
    type: string
    required: true
      - name: file
    in: formData
    type: file
    required: true
    description: MP4 видео файл (макс. 50MB)
      - name: context_description
    in: formData
    type: string
    required: true
    description: Описание контекста использования
      - name: order
    in: formData
    type: integer
    required: false
    default: 0
    description: Порядок отображения
    responses:
      201:
    description: Видео загружено
      400:
    description: Ошибка валидации
      404:
    description: Жест не найден
    """
    Sign.query.get_or_404(sign_id)
        
    if 'file' not in request.files:
            return error_response('NO_FILE', 'Файл не загружен', 400)
        
    file = request.files['file']
    if not file.filename:
            return error_response('NO_FILE', 'Файл не выбран', 400)
        
        # Валидация
    form_data = {
            'context_description': request.form.get('context_description', ''),
            'order': request.form.get('order', 0)
        }
    errors = validate_video_data(form_data, file)
    if errors:
            return validation_error_response(errors)
        
        # Проверка формата
    if not file.filename.lower().endswith('.mp4'):
            return error_response('INVALID_FORMAT', 'Поддерживается только формат MP4', 400)
        
        # Проверка размера
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
        
    if file_size > current_app.config['VIDEO_MAX_SIZE']:
            max_size_mb = VIDEO_MAX_SIZE // (1024 * 1024)
            return error_response(
                'FILE_TOO_LARGE',
                f'Размер файла не должен превышать {max_size_mb}MB',
                400
            )
        
        # Сохранение файла через абстракцию хранилища
    storage = get_video_storage()
    file_path, url = storage.upload(file, sign_id, file.filename)
        
        # Создание записи в БД
    video = SignVideo(
            sign_id=sign_id,
            file_path=file_path,
            url=url,
            context_description=request.form['context_description'],
            order=int(request.form.get('order', 0))
        )
    db.session.add(video)
    db.session.commit()
        
        # Обновление метаданных синхронизации
    update_sync_metadata()
        
    return success_response(data=video.to_dict(), status_code=201)


@bp.route('/videos/<int:video_id>', methods=['PUT'])
@require_auth
@require_json
@handle_db_errors('обновления видео')
def update_video(video_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Обновление видео
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: video_id
    in: path
    type: integer
    required: true
      - name: body
    in: body
    required: true
    schema:
          type: object
          properties:
            context_description:
              type: string
            order:
              type: integer
    responses:
      200:
    description: Видео обновлено
      404:
    description: Видео не найдено
    """
    video = SignVideo.query.get_or_404(video_id)
    data = request.get_json()
        
    if 'context_description' in data:
            video.context_description = data['context_description']
    if 'order' in data:
            video.order = int(data['order'])
        
    db.session.commit()
        
        # Обновление метаданных синхронизации
    update_sync_metadata()
        
    return success_response(data=video.to_dict())


@bp.route('/videos/<int:video_id>', methods=['DELETE'])
@require_auth
@handle_db_errors('удаления видео')
def delete_video(video_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Удаление видео
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: video_id
    in: path
    type: integer
    required: true
    responses:
      200:
    description: Видео удалено
      404:
    description: Видео не найдено
    """
    video = SignVideo.query.get_or_404(video_id)
        
        # Удаление файла через абстракцию хранилища
    storage = get_video_storage()
    if not storage.delete(video.file_path):
            current_app.logger.warning(f"Не удалось удалить файл {video.file_path}")
        
    db.session.delete(video)
    db.session.commit()
        
        # Обновление метаданных синхронизации
    update_sync_metadata()
        
    return success_response(message='Видео удалено')
