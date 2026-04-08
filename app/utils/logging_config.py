"""
Конфигурация структурированного логирования для Loki.
Практическая работа №4 - Berchik Anastasia Sergeevna

Модуль обеспечивает:
- JSON-форматирование логов для парсинга в Loki
- Добавление контекстной информации (request_id, user, route, etc.)
- Запись в файл и stdout
"""
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict

from flask import g, has_request_context, request


_LOG_RESERVED_KEYS = {
    "timestamp",
    "level",
    "message",
    "module",
    "function",
    "line",
    "logger",
    "service",
    "environment",
    "author",
    "request_id",
    "method",
    "path",
    "route",
    "endpoint",
    "blueprint",
    "status_code",
    "status_family",
    "duration_ms",
    "user_id",
    "username",
    "ip_address",
    "user_agent",
    "event_kind",
    "event_domain",
    "event_name",
    "resource",
    "action",
    "outcome",
    "exception",
    "extra",
}


def _json_default(value: Any) -> str:
    """Безопасная сериализация значений для JSON логов."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _normalize_event_name(event: str) -> str:
    """Приводит название события к безопасному snake_case."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", event.strip().lower())
    return normalized.strip("_") or "application_event"


def _derive_event_domain(path: str, blueprint: str = "") -> str:
    """Определяет функциональную область запроса по пути/blueprint."""
    if path.startswith("/api/v1/sync"):
        return "sync"
    if path.startswith("/api/v1/search"):
        return "search"
    if path.startswith("/api/v1/admin/auth"):
        return "admin_auth"
    if path.startswith("/api/v1/admin"):
        return "admin_api"
    if path.startswith("/admin"):
        return "admin_web"
    if path.startswith("/videos"):
        return "videos"
    if path.startswith("/api-docs") or path.startswith("/apispec"):
        return "docs"
    if blueprint:
        return blueprint
    return "application"


def _status_family(status_code: Any) -> str:
    """Возвращает семейство HTTP статуса в формате 2xx/4xx."""
    try:
        status_code = int(status_code)
    except (TypeError, ValueError):
        return "unknown"
    return f"{status_code // 100}xx"


def _request_context() -> Dict[str, Any]:
    """Собирает доступный request context для логов."""
    if not has_request_context():
        return {}

    route = request.url_rule.rule if request.url_rule else request.path
    blueprint = request.blueprint or ""
    endpoint = request.endpoint or ""

    context = {
        "request_id": getattr(g, "request_id", None),
        "method": request.method,
        "path": request.path,
        "route": route,
        "endpoint": endpoint,
        "blueprint": blueprint,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "user_id": getattr(g, "user_id", None),
        "username": getattr(g, "username", None),
        "event_domain": _derive_event_domain(request.path, blueprint),
    }

    return {key: value for key, value in context.items() if value not in (None, "")}


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
            "service": os.getenv("LOG_SERVICE_NAME", "sign-language-backend"),
            "environment": os.getenv("FLASK_ENV", "production"),
            "author": "berchik-as",
        }

        for field_name in (
            "request_id",
            "method",
            "path",
            "route",
            "endpoint",
            "blueprint",
            "status_code",
            "status_family",
            "duration_ms",
            "user_id",
            "username",
            "ip_address",
            "user_agent",
            "event_kind",
            "event_domain",
            "event_name",
            "resource",
            "action",
            "outcome",
        ):
            if hasattr(record, field_name):
                log_data[field_name] = getattr(record, field_name)

        if "status_code" in log_data and "status_family" not in log_data:
            log_data["status_family"] = _status_family(log_data["status_code"])

        log_data.setdefault("event_kind", "application")

        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
            if isinstance(record.extra_data, dict):
                for key, value in record.extra_data.items():
                    if key not in _LOG_RESERVED_KEYS and key not in log_data:
                        log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=_json_default)


class RequestContextFilter(logging.Filter):
    """Фильтр для добавления контекста запроса в логи."""

    def filter(self, record: logging.LogRecord) -> bool:
        for field_name, value in _request_context().items():
            if not hasattr(record, field_name):
                setattr(record, field_name, value)
        return True


def setup_logging(app) -> None:
    """
    Настройка логирования для Flask приложения.
    
    Args:
        app: Flask application instance
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json")
    log_file = os.getenv("LOG_FILE", "/var/log/app/application.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.handlers = []

    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)

    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        root_logger.warning(f"Не удалось создать файловый логгер: {e}")

    app.logger.handlers = root_logger.handlers
    app.logger.setLevel(getattr(logging, log_level))

    app.logger.info("Логирование настроено", extra={
        "event_kind": "lifecycle",
        "event_domain": "application",
        "event_name": "logging_configured",
        "extra_data": {
            "log_level": log_level,
            "log_format": log_format,
            "log_file": log_file,
        },
    })


def log_request():
    """Декоратор/функция для логирования HTTP запросов."""
    from time import time

    def before_request():
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        g.request_id = (request_id or str(uuid.uuid4()))[:64]
        g.start_time = time()

    def after_request(response):
        from flask import current_app

        if not hasattr(g, "start_time"):
            return response

        duration_ms = round((time() - g.start_time) * 1000, 2)
        status_code = response.status_code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        route = request.url_rule.rule if request.url_rule else request.path
        status_family = _status_family(status_code)
        if status_code >= 500:
            outcome = "server_error"
        elif status_code >= 400:
            outcome = "client_error"
        else:
            outcome = "success"

        log_record = current_app.logger.makeRecord(
            name=current_app.logger.name,
            level=log_level,
            fn="",
            lno=0,
            msg=f"{request.method} {request.path} -> {response.status_code}",
            args=(),
            exc_info=None,
        )
        log_record.method = request.method
        log_record.path = request.path
        log_record.route = route
        log_record.endpoint = request.endpoint or ""
        log_record.blueprint = request.blueprint or ""
        log_record.status_code = response.status_code
        log_record.status_family = status_family
        log_record.duration_ms = duration_ms
        log_record.ip_address = request.remote_addr
        log_record.user_agent = request.headers.get("User-Agent", "")
        log_record.event_kind = "request"
        log_record.event_domain = _derive_event_domain(request.path, request.blueprint or "")
        log_record.event_name = "http_request"
        log_record.outcome = outcome

        if hasattr(g, "user_id"):
            log_record.user_id = g.user_id
        if hasattr(g, "username"):
            log_record.username = g.username

        current_app.logger.handle(log_record)

        return response

    return before_request, after_request


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
def log_business_event(
    logger: logging.Logger,
    event: str,
    details: Dict[str, Any] = None,
    **event_fields: Any,
) -> None:
    """Логирование бизнес-события."""
    extra = {
        "event_kind": "business",
        "event_name": event_fields.pop("event_name", _normalize_event_name(event)),
        "extra_data": details or {},
    }
    extra.update({key: value for key, value in event_fields.items() if value is not None})
    logger.info(event, extra=extra)


def log_error_with_context(
    logger: logging.Logger,
    message: str,
    error: Exception,
    context: Dict[str, Any] = None,
    **event_fields: Any,
) -> None:
    """Логирование ошибки с контекстом."""
    extra = {
        "event_kind": "application",
        "event_name": event_fields.pop("event_name", _normalize_event_name(message)),
        "outcome": event_fields.pop("outcome", "failure"),
        "extra_data": context or {},
    }
    extra.update({key: value for key, value in event_fields.items() if value is not None})
    logger.error(message, exc_info=True, extra=extra)
