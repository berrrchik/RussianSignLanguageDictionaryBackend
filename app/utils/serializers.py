"""
Утилиты для сериализации данных в формат оптимизированный для мобильных клиентов.

Этот модуль предоставляет функции для преобразования datetime объектов
в Unix timestamp (секунды) и обратно для упрощения работы iOS/Android клиентов.
"""
from datetime import datetime, timezone
from typing import Optional


def serialize_datetime(dt: Optional[datetime]) -> Optional[int]:
    """
    Преобразует datetime в Unix timestamp (секунды).
    
    Args:
        dt: datetime объект или None
        
    Returns:
        Unix timestamp в секундах (целое число) или None
        
    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> serialize_datetime(dt)
        1736935800
        
        >>> serialize_datetime(None)
        None
    """
    if dt is None:
        return None
    
    # Если datetime naive (без timezone), предполагаем UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return int(dt.timestamp())


def deserialize_datetime(timestamp: Optional[int]) -> Optional[datetime]:
    """
    Преобразует Unix timestamp в datetime (UTC).
    
    Args:
        timestamp: Unix timestamp в секундах или None
        
    Returns:
        datetime объект в UTC timezone или None
        
    Examples:
        >>> deserialize_datetime(1736935800)
        datetime.datetime(2025, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        
        >>> deserialize_datetime(None)
        None
    """
    if timestamp is None:
        return None
    
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
