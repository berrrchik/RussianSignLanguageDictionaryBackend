"""
Абстракция для хранения видео файлов.
Позволяет легко переключаться между локальным хранилищем и удаленным (Supabase, сервер ВОГ).
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
from werkzeug.utils import secure_filename


class VideoStorage(ABC):
    """Абстрактный класс для хранения видео."""
    
    @abstractmethod
    def upload(self, file, sign_id: str, filename: str, category_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Загружает видео файл.
        
        Args:
            file: Файловый объект для загрузки
            sign_id: ID жеста
            filename: Имя файла
            category_id: ID категории (опционально, используется для структуры папок в Supabase)
            
        Returns:
            Tuple[file_path, url]: Путь к файлу и публичный URL
        """
        pass
    
    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """
        Удаляет видео файл.
        
        Args:
            file_path: Путь к файлу для удаления
            
        Returns:
            True если удалено успешно, False иначе
        """
        pass
    
    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """
        Получает публичный URL для файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Публичный URL
        """
        pass


class LocalVideoStorage(VideoStorage):
    """Локальное хранилище видео (для разработки)."""
    
    def __init__(self, storage_path: str, base_url: str):
        """
        Инициализация локального хранилища.
        
        Args:
            storage_path: Путь к директории для хранения видео
            base_url: Базовый URL для доступа к видео
        """
        self.storage_path = Path(storage_path)
        self.base_url = base_url.rstrip('/')
        
        # Создание директории если не существует
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def upload(self, file, sign_id: str, filename: str, category_id: Optional[str] = None) -> Tuple[str, str]:
        """Загружает файл в локальное хранилище."""
        # Безопасное имя файла с префиксом sign_id
        safe_filename = secure_filename(filename)
        safe_filename = f"{sign_id}_{safe_filename}"
        
        file_path = self.storage_path / safe_filename
        file.save(str(file_path))
        
        # Генерация URL
        url = f"{self.base_url}/{safe_filename}"
        
        return (str(file_path), url)
    
    def delete(self, file_path: str) -> bool:
        """Удаляет файл из локального хранилища."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_url(self, file_path: str) -> str:
        """Получает публичный URL для локального файла."""
        filename = Path(file_path).name
        return f"{self.base_url}/{filename}"


class SupabaseVideoStorage(VideoStorage):
    """Хранилище видео в Supabase Storage."""
    
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str = "signs"):
        """
        Инициализация Supabase хранилища.
        
        Args:
            supabase_url: URL проекта Supabase
            supabase_key: API ключ Supabase (должен быть service role key для загрузки)
            bucket_name: Имя bucket в Supabase Storage
        """
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name
        
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except ImportError:
            raise ImportError("Библиотека supabase не установлена. Установите: pip install supabase")
    
    def upload(self, file, sign_id: str, filename: str, category_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Загружает файл в Supabase Storage.
        
        Args:
            file: Файловый объект для загрузки
            sign_id: ID жеста
            filename: Исходное имя файла
            category_id: ID категории (используется для структуры папок: signs/{category_id}/filename)
            
        Returns:
            Tuple[file_path, url]: Относительный путь для БД и публичный URL
        """
        from werkzeug.utils import secure_filename
        
        safe_filename = secure_filename(filename)
        safe_sign_id = sign_id.replace('_', '-')
        safe_filename = f"{safe_sign_id}-{safe_filename}"
        
        if category_id:
            safe_category_id = category_id.replace('_', '-')
            storage_path = f"signs/{safe_category_id}/{safe_filename}"
        else:
            storage_path = safe_filename
        
        file.seek(0)
        file_data = file.read()
        
        self.client.storage.from_(self.bucket_name).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "video/mp4", "upsert": "true"}
        )
        
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(storage_path)
        
        if category_id:
            safe_category_id = category_id.replace('_', '-')
            file_path = f"signs/{safe_category_id}/{safe_filename}"
        else:
            file_path = f"signs/{safe_filename}"
        
        return (file_path, public_url)
    
    def delete(self, file_path: str) -> bool:
        """
        Удаляет файл из Supabase Storage.
        
        Args:
            file_path: Относительный путь в формате signs/category/filename или signs/filename
            
        Returns:
            True если удалено успешно, False иначе
        """
        try:
            storage_path = file_path
            
            self.client.storage.from_(self.bucket_name).remove([storage_path])
            return True
        except Exception as e:  
            import logging
            logging.warning(f"Не удалось удалить файл {file_path} из Supabase Storage: {e}")
            return False
    
    def get_url(self, file_path: str) -> str:
        """
        Получает публичный URL для файла в Supabase.
        
        Args:
            file_path: Относительный путь в формате signs/category/filename или signs/filename
            
        Returns:
            Публичный URL
        """
        storage_path = file_path
        
        return self.client.storage.from_(self.bucket_name).get_public_url(storage_path)


def get_video_storage():
    """
    Фабрика для получения экземпляра хранилища видео.
    
    Использует конфигурацию из переменных окружения:
    - VIDEO_STORAGE_TYPE: 'local' или 'supabase' (по умолчанию 'local')
    - Для local: VIDEO_STORAGE_PATH, VIDEO_BASE_URL
    - Для supabase: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (или SUPABASE_KEY), SUPABASE_BUCKET
    
    Returns:
        Экземпляр VideoStorage
    """
    from flask import current_app
    
    storage_type = os.getenv('VIDEO_STORAGE_TYPE', 'local').lower()
    
    if storage_type == 'local':
        return LocalVideoStorage(
            storage_path=current_app.config['VIDEO_STORAGE_PATH'],
            base_url=current_app.config['VIDEO_BASE_URL']
        )
    elif storage_type == 'supabase':
        supabase_url = os.getenv('SUPABASE_URL')
        # Используем service role key для загрузки (обходит RLS), если доступен, иначе anon key
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        bucket_name = os.getenv('SUPABASE_BUCKET', 'signs')
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Настройки Supabase не найдены. Укажите SUPABASE_URL и "
                "SUPABASE_KEY (или SUPABASE_SERVICE_ROLE_KEY) в .env"
            )
        
        return SupabaseVideoStorage(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            bucket_name=bucket_name
        )
    else:
        raise ValueError(f"Неизвестный тип хранилища: {storage_type}")

