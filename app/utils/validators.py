"""
Валидация данных для API.
"""
from typing import Dict, List, Optional, Tuple, Type, Any

from app.constants import (
    MAX_WORD_LENGTH,
    MAX_CATEGORY_NAME_LENGTH,
    MAX_CATEGORY_ID_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_CONTEXT_DESCRIPTION_LENGTH,
    VIDEO_MAX_SIZE
)
from app.utils.responses import error_response


def validate_sign_data(data: Dict) -> List[str]:
    """
    Валидация данных для создания/обновления жеста.
    
    Args:
        data: Словарь с данными жеста
        
    Returns:
        Список ошибок валидации (пустой если всё ок)
    """
    errors = []
    
    if 'word' in data:
        word = data['word']
        if not word or not isinstance(word, str):
            errors.append('Поле "word" должно быть непустой строкой')
        elif len(word) > MAX_WORD_LENGTH:
            errors.append(f'Поле "word" не должно превышать {MAX_WORD_LENGTH} символов')
    
    if 'category_id' in data:
        category_id = data['category_id']
        if not category_id or not isinstance(category_id, str):
            errors.append('Поле "category_id" должно быть непустой строкой')
        elif len(category_id) > MAX_CATEGORY_ID_LENGTH:
            errors.append(f'Поле "category_id" не должно превышать {MAX_CATEGORY_ID_LENGTH} символов')
    
    if 'description' in data and data['description'] is not None:
        if not isinstance(data['description'], str):
            errors.append('Поле "description" должно быть строкой')
    
    return errors


def validate_category_data(data: Dict) -> List[str]:
    """
    Валидация данных для создания/обновления категории.
    
    Args:
        data: Словарь с данными категории
        
    Returns:
        Список ошибок валидации (пустой если всё ок)
    """
    errors = []
    
    if 'name' in data:
        name = data['name']
        if not name or not isinstance(name, str):
            errors.append('Поле "name" должно быть непустой строкой')
        elif len(name) > MAX_CATEGORY_NAME_LENGTH:
            errors.append(f'Поле "name" не должно превышать {MAX_CATEGORY_NAME_LENGTH} символов')
    
    if 'order' in data:
        order = data['order']
        if not isinstance(order, int):
            errors.append('Поле "order" должно быть целым числом')
        elif order < 0:
            errors.append('Поле "order" должно быть неотрицательным')
    
    return errors


def validate_video_data(data: Dict, file=None) -> List[str]:
    """
    Валидация данных для загрузки видео.
    
    Args:
        data: Словарь с данными видео
        file: Загружаемый файл
        
    Returns:
        Список ошибок валидации (пустой если всё ок)
    """
    errors = []
    
    if file:
        # Проверка расширения файла
        if not file.filename:
            errors.append('Файл не указан')
        elif not file.filename.lower().endswith('.mp4'):
            errors.append('Поддерживается только формат MP4')
        
        # Проверка размера файла
        if hasattr(file, 'content_length') and file.content_length:
            if file.content_length > VIDEO_MAX_SIZE:
                max_size_mb = VIDEO_MAX_SIZE // (1024 * 1024)
                errors.append(f'Размер файла не должен превышать {max_size_mb}MB')
    
    if 'context_description' in data:
        context_description = data.get('context_description')
        if not context_description or not isinstance(context_description, str):
            errors.append('Поле "context_description" должно быть непустой строкой')
    
    if 'order' in data:
        order = data.get('order')
        if order is not None and not isinstance(order, int):
            errors.append('Поле "order" должно быть целым числом')
    
    return errors


def validate_lesson_data(data: dict, require_id: bool = False, require_video: bool = False) -> Tuple[bool, str]:
    """
    Валидация данных для создания/обновления урока.
    
    Args:
        data: Словарь с данными урока
        require_id: Если True, ID обязателен (для обновления), иначе опционален (для создания)
        require_video: Если True, video_url обязателен (для создания урока)
        
    Returns:
        Tuple[is_valid: bool, error_message: str] - кортеж с результатом валидации
    """
    # ID опционален при создании (будет автогенерирован), обязателен при обновлении
    if require_id:
        if not data.get('id') or len(data['id']) > 50:
            return False, "ID обязателен и должен быть не длиннее 50 символов"
    elif data.get('id') and len(data['id']) > 50:
        return False, "ID должен быть не длиннее 50 символов"
    
    if not data.get('title') or len(data['title']) > 200:
        return False, "Title обязателен и должен быть не длиннее 200 символов"
    
    if not data.get('description'):
        return False, "Description обязателен"
    
    # video_url обязателен при создании (require_video=True)
    # при обновлении может быть пустым (если видео было удалено)
    if require_video and not data.get('video_url'):
        return False, "Video URL обязателен при создании урока"
    
    # При обновлении, если video_url пустой, это допустимо (видео было удалено)
    
    order = data.get('order')
    if order is None or not isinstance(order, int) or order < 0:
        return False, "Order должен быть неотрицательным целым числом"
    
    return True, ""


def validate_entity_exists(
    model_class: Type,
    entity_id: Any,
    entity_name: Optional[str] = None
) -> Tuple[Optional[Any], Optional[Tuple]]:
    """
    Проверяет существование сущности в БД.
    
    Args:
        model_class: Класс модели SQLAlchemy
        entity_id: ID сущности
        entity_name: Название сущности для сообщения об ошибке
        
    Returns:
        Tuple[entity, error_response] - если entity None, нужно вернуть error_response
        
    Example:
        category, error = validate_entity_exists(Category, data['category_id'], 'Категория')
        if error:
            return error
    """
    entity = model_class.query.get(entity_id)
    if not entity:
        name = entity_name or model_class.__name__
        return None, error_response(
            f'{name.upper()}_NOT_FOUND',
            f'{name} не найдена',
            400
        )
    return entity, None

