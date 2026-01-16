"""
Модуль административных endpoints.
Объединяет все подмодули в единый blueprint.
"""
from flask import Blueprint

from app.routes.admin import auth, signs, videos, categories, synonyms, pages, lessons

# Основной blueprint для API endpoints
bp = Blueprint('admin', __name__)

# Регистрация всех подмодулей
bp.register_blueprint(auth.bp)
bp.register_blueprint(signs.bp)
bp.register_blueprint(videos.bp)
bp.register_blueprint(categories.bp)
bp.register_blueprint(synonyms.bp)
bp.register_blueprint(lessons.bp)

# Отдельный blueprint для HTML страниц
admin_pages_bp = pages.bp

