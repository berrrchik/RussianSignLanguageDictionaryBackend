"""
Конфигурация приложения через переменные окружения.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()


class Config:
    """Базовая конфигурация приложения."""
    
    # База данных
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/sign_language_dict'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
    JWT_EXPIRATION_DELTA = int(os.getenv('JWT_EXPIRATION_DELTA', 3600))
    
    # Хранение видео
    VIDEO_STORAGE_TYPE = os.getenv('VIDEO_STORAGE_TYPE', 'local')  # 'local' или 'supabase'
    VIDEO_STORAGE_PATH = os.getenv('VIDEO_STORAGE_PATH', 'static/videos')
    # Порт берётся из FLASK_PORT или по умолчанию 5001
    flask_port = int(os.getenv('FLASK_PORT', 5001))
    VIDEO_BASE_URL = os.getenv('VIDEO_BASE_URL', f'http://localhost:{flask_port}/videos')
    VIDEO_MAX_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Supabase (для будущего использования)
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET', 'signs')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY') or JWT_SECRET_KEY
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией."""
        # Создание директории для видео если используется локальное хранилище
        if app.config.get('VIDEO_STORAGE_TYPE', 'local') == 'local':
            video_path = Path(app.config['VIDEO_STORAGE_PATH'])
            video_path.mkdir(parents=True, exist_ok=True)

