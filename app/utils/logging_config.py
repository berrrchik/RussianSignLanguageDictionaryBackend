"""
Конфигурация структурированного логирования для Loki.
Практическая работа №4 - Berchik Anastasia Sergeevna

Модуль обеспечивает:
- JSON-форматирование логов для парсинга в Loki
- Добавление контекстной информации (request_id, user, etc.)
- Запись в файл и stdout
"""
import logging
import json
import os
import sys
import uuid
from datetime import datetime
from functools import wraps
from flask import request, g
from typing import Optional, Any


class JSONFormatter(logging.Formatter):
    """
    JSON-форматтер для структурированных логов.
    Формат оптимизирован для парсинга в Loki/Promtail.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "logger": record.name,
            "author": "berchik-as"
        }
        
        # Добавление request_id если есть
        try:
            if hasattr(g, 'request_id'):
                log_data["request_id"] = g.request_id
        except RuntimeError:
            # Вне контекста запроса
            pass
        
        # Добавление HTTP информации если есть
        if hasattr(record, 'method'):
            log_data["method"] = record.method
        if hasattr(record, 'path'):
            log_data["path"] = record.path
        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'ip_address'):
            log_data["ip_address"] = record.ip_address
        if hasattr(record, 'user_agent'):
            log_data["user_agent"] = record.user_agent
            
        # Добавление extra данных
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
            
        # Добавление информации об исключении
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """Фильтр для добавления контекста запроса в логи."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Добавляем request_id если доступен
        try:
            if hasattr(g, 'request_id'):
                record.request_id = g.request_id
            if hasattr(g, 'user_id'):
                record.user_id = g.user_id
        except RuntimeError:
            # Вне контекста запроса
            pass
        return True


def setup_logging(app) -> None:
    """
    Настройка логирования для Flask приложения.
    
    Args:
        app: Flask application instance
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', 'json')
    log_file = os.getenv('LOG_FILE', '/var/log/app/application.log')
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Очищаем существующие хендлеры
    root_logger.handlers = []
    
    # Выбор форматтера
    if log_format == 'json':
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Консольный хендлер
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)
    
    # Файловый хендлер (для Promtail)
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        root_logger.warning(f"Не удалось создать файловый логгер: {e}")
    
    # Настройка логгера Flask
    app.logger.handlers = root_logger.handlers
    app.logger.setLevel(getattr(logging, log_level))
    
    # Логирование запуска
    app.logger.info("Логирование настроено", extra={
        'extra_data': {
            'log_level': log_level,
            'log_format': log_format,
            'log_file': log_file
        }
    })


def log_request():
    """Декоратор/функция для логирования HTTP запросов."""
    from time import time
    
    def before_request():
        g.request_id = str(uuid.uuid4())[:8]
        g.start_time = time()
    
    def after_request(response):
        from flask import current_app
        
        duration_ms = round((time() - g.start_time) * 1000, 2)
        
        # Определяем уровень лога на основе HTTP статуса
        status_code = response.status_code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        # Создаем запись лога с дополнительными атрибутами
        log_record = current_app.logger.makeRecord(
            name=current_app.logger.name,
            level=log_level,
            fn="",
            lno=0,
            msg=f"{request.method} {request.path} -> {response.status_code}",
            args=(),
            exc_info=None
        )
        log_record.method = request.method
        log_record.path = request.path
        log_record.status_code = response.status_code
        log_record.duration_ms = duration_ms
        log_record.ip_address = request.remote_addr
        log_record.user_agent = request.headers.get('User-Agent', '')
        
        # Добавляем user_id если есть
        try:
            if hasattr(g, 'user_id'):
                log_record.user_id = g.user_id
        except RuntimeError:
            pass
        
        current_app.logger.handle(log_record)
        
        return response
    
    return before_request, after_request
# 
# 
def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с настроенным форматированием.
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


# Вспомогательные функции для логирования бизнес-событий
def log_business_event(logger: logging.Logger, event: str, details: dict = None):
    """Логирование бизнес-события."""
    logger.info(event, extra={'extra_data': details or {}})


def log_error_with_context(logger: logging.Logger, message: str, error: Exception, context: dict = None):
    """Логирование ошибки с контекстом."""
    logger.error(message, exc_info=True, extra={'extra_data': context or {}})
