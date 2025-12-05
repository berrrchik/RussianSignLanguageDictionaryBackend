"""
Утилиты для форматирования данных.
"""
from datetime import datetime
from typing import Optional


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Форматирует datetime в ISO 8601 с суффиксом 'Z' (UTC).
    
    Args:
        dt: datetime объект или None
        
    Returns:
        Строка в формате ISO 8601 с 'Z' или None
        
    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 12, 4, 12, 7, 58, 765345)
        >>> format_datetime(dt)
        '2025-12-04T12:07:58.765345Z'
    """
    if dt is None:
        return None
    
    # Преобразуем в naive datetime если есть timezone info
    if dt.tzinfo is not None:
        # Убираем timezone info, так как в БД используются naive datetime (предполагается UTC)
        dt = dt.replace(tzinfo=None)
    
    # Получаем ISO строку
    iso_str = dt.isoformat()
    
    # Убеждаемся, что есть 'Z' в конце
    if not iso_str.endswith('Z'):
        iso_str = iso_str + 'Z'
    
    return iso_str
