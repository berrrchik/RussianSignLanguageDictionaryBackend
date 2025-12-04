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
from app.utils.responses import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    internal_error_response
)
from app.constants import VIDEO_MAX_SIZE

bp = Blueprint('admin_videos', __name__)


@bp.route('/signs/<sign_id>/videos', methods=['GET'])
@require_auth
def list_videos(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Получение списка видео для жеста.
    
    Args:
        sign_id: ID жеста
        
    Returns:
        JSON ответ со списком видео
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        videos = SignVideo.query.filter_by(sign_id=sign_id).order_by(SignVideo.order).all()
        return success_response(data=[video.to_dict() for video in videos])
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка видео: {e}")
        return internal_error_response('Ошибка получения списка видео')


@bp.route('/signs/<sign_id>/videos', methods=['POST'])
@require_auth
def upload_video(sign_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Загрузка видео для жеста.
    
    Args:
        sign_id: ID жеста
        
    Returns:
        JSON ответ с загруженным видео
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        
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
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка загрузки видео: {e}")
        return internal_error_response('Ошибка загрузки видео')


@bp.route('/videos/<int:video_id>', methods=['PUT'])
@require_auth
def update_video(video_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Обновление видео.
    
    Args:
        video_id: ID видео
        
    Returns:
        JSON ответ с обновленным видео
    """
    try:
        video = SignVideo.query.get_or_404(video_id)
        data = request.get_json()
        
        if not data:
            return error_response('INVALID_REQUEST', 'Требуется JSON тело запроса', 400)
        
        if 'context_description' in data:
            video.context_description = data['context_description']
        if 'order' in data:
            video.order = int(data['order'])
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return success_response(data=video.to_dict())
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления видео: {e}")
        return internal_error_response('Ошибка обновления видео')


@bp.route('/videos/<int:video_id>', methods=['DELETE'])
@require_auth
def delete_video(video_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Удаление видео.
    
    Args:
        video_id: ID видео
        
    Returns:
        JSON ответ об успешном удалении
    """
    try:
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
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления видео: {e}")
        return internal_error_response('Ошибка удаления видео')

