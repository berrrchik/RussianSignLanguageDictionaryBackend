"""
Утилиты для генерации ETag заголовков.
"""
import hashlib
import json
from typing import Optional, Tuple
from flask import request, make_response, current_app, jsonify, Response


def generate_etag(data: dict) -> str:
    """
    Генерирует ETag на основе содержимого данных.
    
    Args:
        data: Словарь с данными для генерации ETag
        
    Returns:
        MD5 хеш от JSON представления данных
    """
    data_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(data_json.encode('utf-8')).hexdigest()


def normalize_etag(etag: str) -> str:
    """
    Нормализует ETag, удаляя суффиксы вариантов представления (например, :gzip) и кавычки.
    
    Согласно RFC 7232, ETag может иметь суффиксы для разных вариантов представления:
    - "abc123:gzip" - для gzip сжатого варианта
    - "abc123:deflate" - для deflate сжатого варианта
    
    При сравнении нужно сравнивать только основную часть ETag (до двоеточия).
    
    Args:
        etag: ETag строка, возможно с суффиксом и кавычками
        
    Returns:
        Нормализованный ETag без суффиксов и кавычек
    """
    if not etag:
        return ""
    
    # Удаляем кавычки в начале и конце (может быть несколько кавычек)
    etag = etag.strip()
    # Удаляем все кавычки
    etag = etag.replace('"', '').replace("'", '')
    
    # Удаляем суффиксы вариантов представления (например, :gzip, :deflate)
    # Паттерн: двоеточие, затем любые буквы/цифры до конца строки
    # Важно: не удаляем часть хеша, только суффиксы после двоеточия
    # MD5 хеш всегда 32 символа, так что если после двоеточия больше 32 символов - это суффикс
    if ':' in etag:
        # Разделяем по двоеточию
        parts = etag.split(':')
        # Первая часть - это ETag (должна быть 32 символа для MD5)
        main_etag = parts[0]
        # Если основная часть короче 32 символов, возможно клиент обрезал ETag
        # В этом случае возвращаем как есть (без суффикса)
        if len(main_etag) <= 32:
            return main_etag
        else:
            # Если больше 32 символов, значит что-то не так - возвращаем первые 32
            return main_etag[:32]
    
    return etag


def check_etag_match(computed_etag: str, endpoint_name: str) -> Optional[object]:
    """
    Проверяет совпадение ETag из запроса с вычисленным ETag.
    
    Если ETag совпадает, возвращает 304 Not Modified ответ.
    Если не совпадает или отсутствует, возвращает None (нужно продолжить обработку).
    
    Args:
        computed_etag: Вычисленный ETag для текущих данных
        endpoint_name: Имя endpoint'а для логирования (например, "/sync/data/raw")
        
    Returns:
        Response объект с 304 статусом, если ETag совпадает, иначе None
    """
    if_none_match = request.headers.get('If-None-Match')
    
    if if_none_match:
        # Нормализуем ETag из запроса (удаляем суффиксы типа :gzip)
        normalized_if_none_match = normalize_etag(if_none_match)
        
        if normalized_if_none_match == computed_etag:
            current_app.logger.info(f"ETag match for {endpoint_name}: 304 returned")
            return make_response('', 304)
        elif len(normalized_if_none_match) < len(computed_etag) and computed_etag.startswith(normalized_if_none_match):
            # Клиент сохранил неполный ETag (возможно, обрезан при сохранении)
            # MD5 хеш всегда 32 символа, если клиент отправил меньше - это ошибка на клиенте
            # Но для обратной совместимости можем проверить начало
            # Однако, лучше не возвращать 304, так как ETag не полностью совпадает
            # и данные могли измениться
            current_app.logger.warning(
                f"ETag partial match (incomplete client ETag) for {endpoint_name}: "
                f"old={if_none_match} (normalized={normalized_if_none_match}, len={len(normalized_if_none_match)}), "
                f"new={computed_etag} (len={len(computed_etag)}). "
                f"Client saved incomplete ETag - returning 200 to ensure data consistency."
            )
            # Не возвращаем 304, так как ETag не полностью совпадает
        current_app.logger.debug(
            f"ETag mismatch for {endpoint_name}: "
            f"old={if_none_match} (normalized={normalized_if_none_match}, len={len(normalized_if_none_match)}), "
            f"new={computed_etag} (len={len(computed_etag)})"
        )
    else:
        current_app.logger.debug(f"ETag for {endpoint_name}: first request, new={computed_etag}")
    
    return None


def create_response_with_etag(data: dict, endpoint_path: str) -> Tuple[Response, int]:
    """
    Создает JSON ответ с ETag заголовком.
    
    Генерирует ETag, проверяет условный запрос (If-None-Match),
    и возвращает либо 304 Not Modified, либо полный ответ с ETag.
    
    Args:
        data: Данные для ответа
        endpoint_path: Путь эндпоинта для логирования
        
    Returns:
        Tuple[Response, status_code] - Flask Response с ETag заголовком и статус код
    """
    etag = generate_etag(data)
    
    # Проверка условного запроса
    etag_response = check_etag_match(etag, endpoint_path)
    if etag_response:
        return etag_response, 304
    
    # Проверяем, что ETag имеет правильную длину (32 символа для MD5)
    if len(etag) != 32:
        current_app.logger.error(
            f"КРИТИЧЕСКАЯ ОШИБКА: ETag имеет неправильную длину для {endpoint_path}: "
            f"len={len(etag)}, etag={etag}"
        )
    
    json_response = jsonify(data)
    json_response.headers['ETag'] = f'"{etag}"'
    
    current_app.logger.debug(
        f"ETag отправлен в заголовке для {endpoint_path}: "
        f"etag={etag} (len={len(etag)})"
    )
    
    return json_response, 200
