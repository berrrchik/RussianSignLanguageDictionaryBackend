"""
Валидация данных для API.
"""
from typing import Dict, List, Optional


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
        elif len(word) > 200:
            errors.append('Поле "word" не должно превышать 200 символов')
    
    if 'category_id' in data:
        category_id = data['category_id']
        if not category_id or not isinstance(category_id, str):
            errors.append('Поле "category_id" должно быть непустой строкой')
        elif len(category_id) > 50:
            errors.append('Поле "category_id" не должно превышать 50 символов')
    
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
        elif len(name) > 200:
            errors.append('Поле "name" не должно превышать 200 символов')
    
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
        
        # Проверка размера файла (50MB)
        if hasattr(file, 'content_length') and file.content_length:
            max_size = 50 * 1024 * 1024  # 50MB
            if file.content_length > max_size:
                errors.append(f'Размер файла не должен превышать 50MB')
    
    if 'context_description' in data:
        context_description = data.get('context_description')
        if not context_description or not isinstance(context_description, str):
            errors.append('Поле "context_description" должно быть непустой строкой')
    
    if 'order' in data:
        order = data.get('order')
        if order is not None and not isinstance(order, int):
            errors.append('Поле "order" должно быть целым числом')
    
    return errors


def validate_embeddings(embeddings: Optional[List[float]]) -> bool:
    """
    Валидация embeddings перед сохранением в БД.
    
    Args:
        embeddings: Список чисел (embeddings)
        
    Returns:
        True если валидно, False иначе
    """
    if embeddings is None:
        return True  # None допустимо
    
    if not isinstance(embeddings, list):
        return False
    
    if len(embeddings) != 768:
        return False
    
    if not all(isinstance(x, (int, float)) for x in embeddings):
        return False
    
    return True

