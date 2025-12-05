"""
Flask приложение для системы управления словарём русского жестового языка.
"""
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

from app.config import Config
from app.database import db
from app.errors import register_error_handlers


def create_app(config_class=Config):
    """
    Фабрика приложения Flask.
    
    Args:
        config_class: Класс конфигурации
        
    Returns:
        Экземпляр Flask приложения
    """
    import os
    from pathlib import Path
    
    base_dir = Path(__file__).parent.parent
    
    app = Flask(__name__, 
                template_folder=str(base_dir / 'templates'),
                static_folder=str(base_dir / 'static'))
    app.config.from_object(config_class)
    
    config_class.init_app(app)
    db.init_app(app)
    
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # В production указать конкретные домены
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    from app.routes import sync, admin, search
    app.register_blueprint(sync.bp, url_prefix='/api/v1/sync')
    app.register_blueprint(search.bp, url_prefix='/api/v1/search')
    app.register_blueprint(admin.bp, url_prefix='/api/v1/admin')
    
    from app.routes.admin import admin_pages_bp
    app.register_blueprint(admin_pages_bp, url_prefix='/admin')
    
    from flask import send_from_directory
    @app.route('/videos/<filename>')
    def serve_video(filename):
        """Раздача видео файлов."""
        from pathlib import Path
        video_path = Path(app.config['VIDEO_STORAGE_PATH'])
        return send_from_directory(str(video_path), filename)
    
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "API Словаря русского жестового языка",
            "description": "REST API для системы управления словарём русского жестового языка",
            "version": "1.0.0",
            "contact": {
                "name": "ВОГ"
            }
        },
        "basePath": "/api/v1",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT токен. Формат: Bearer {token}"
            }
        },
        "tags": [
            {
                "name": "Синхронизация",
                "description": "Endpoints для синхронизации мобильного приложения"
            },
            {
                "name": "Авторизация",
                "description": "Авторизация администратора"
            },
            {
                "name": "Жесты",
                "description": "CRUD операции для жестов"
            },
            {
                "name": "Категории",
                "description": "CRUD операции для категорий"
            },
            {
                "name": "Видео",
                "description": "Управление видео файлами"
            },
            {
                "name": "Синонимы",
                "description": "Управление синонимами жестов"
            },
            {
                "name": "Поиск",
                "description": "Endpoints для семантического поиска"
            }
        ],
        "definitions": {
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "greetings"},
                    "name": {"type": "string", "example": "Приветствия"},
                    "order": {"type": "integer", "example": 1},
                    "sign_count": {"type": "integer", "example": 15},
                    "created_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"},
                    "updated_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"}
                },
                "required": ["id", "name", "order", "sign_count"]
            },
            "SignVideo": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "url": {"type": "string", "example": "http://example.com/videos/sign_001_video_1.mp4"},
                    "context_description": {"type": "string", "example": "Основное видео"},
                    "order": {"type": "integer", "example": 0},
                    "created_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"},
                    "updated_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"}
                },
                "required": ["id", "url", "context_description", "order"]
            },
            "Sign": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "sign_001"},
                    "word": {"type": "string", "example": "привет"},
                    "description": {"type": "string", "example": "Приветствие"},
                    "category_id": {"type": "string", "example": "greetings"},
                    "embeddings": {
                        "type": "array",
                        "items": {"type": "number"},
                        "example": [0.1, 0.2, 0.3, 0.4, 0.5]
                    },
                    "videos_count": {"type": "integer", "example": 2},
                    "videos": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/SignVideo"}
                    },
                    "synonyms": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "example": "sign_002"},
                                "word": {"type": "string", "example": "здравствуй"}
                            }
                        }
                    },
                    "created_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"},
                    "updated_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"}
                },
                "required": ["id", "word", "category_id"]
            },
            "SignSynonym": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "sign_id_1": {"type": "string", "example": "sign_001"},
                    "sign_id_2": {"type": "string", "example": "sign_002"},
                    "created_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"}
                },
                "required": ["id", "sign_id_1", "sign_id_2"]
            },
            "AdminUser": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "username": {"type": "string", "example": "admin"},
                    "created_at": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"},
                    "last_login": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"}
                },
                "required": ["id", "username"]
            },
            "SyncMetadata": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "example": 1},
                    "last_updated": {"type": "string", "format": "date-time", "example": "2025-12-04T12:07:58.765345Z"},
                    "version": {"type": "integer", "example": 1}
                },
                "required": ["id", "last_updated", "version"]
            },
            "Pagination": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "example": 1},
                    "per_page": {"type": "integer", "example": 50},
                    "total": {"type": "integer", "example": 100},
                    "pages": {"type": "integer", "example": 2}
                },
                "required": ["page", "per_page", "total", "pages"]
            },
            "Error": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "example": "VALIDATION_ERROR"},
                    "message": {"type": "string", "example": "Ошибка валидации данных"}
                },
                "required": ["code", "message"]
            },
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "data": {"type": "object"},
                    "message": {"type": "string", "example": "Операция выполнена успешно"}
                },
                "required": ["success"]
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"$ref": "#/definitions/Error"}
                },
                "required": ["success", "error"]
            }
        }
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    
    register_error_handlers(app)
    
    return app

