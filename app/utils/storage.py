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
    def upload(self, file, sign_id: str, filename: str) -> Tuple[str, str]:
        """
        Загружает видео файл.
        
        Args:
            file: Файловый объект для загрузки
            sign_id: ID жеста
            filename: Имя файла
            
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
    
    def upload(self, file, sign_id: str, filename: str) -> Tuple[str, str]:
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
    """Хранилище видео в Supabase Storage (для будущего использования)."""
    
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str = "signs"):
        """
        Инициализация Supabase хранилища.
        
        Args:
            supabase_url: URL проекта Supabase
            supabase_key: API ключ Supabase
            bucket_name: Имя bucket в Supabase Storage
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name
        # TODO: Инициализировать Supabase клиент когда понадобится
        # from supabase import create_client
        # self.client = create_client(supabase_url, supabase_key)
    
    def upload(self, file, sign_id: str, filename: str) -> Tuple[str, str]:
        """Загружает файл в Supabase Storage."""
        # TODO: Реализовать загрузку в Supabase
        # Путь в формате: signs/{category}/{filename}
        # storage_path = f"signs/{category}/{filename}"
        # response = self.client.storage.from_(self.bucket_name).upload(storage_path, file)
        # url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{storage_path}"
        raise NotImplementedError("Supabase storage будет реализован позже")
    
    def delete(self, file_path: str) -> bool:
        """Удаляет файл из Supabase Storage."""
        # TODO: Реализовать удаление из Supabase
        raise NotImplementedError("Supabase storage будет реализован позже")
    
    def get_url(self, file_path: str) -> str:
        """Получает публичный URL для файла в Supabase."""
        # TODO: Реализовать получение URL из Supabase
        raise NotImplementedError("Supabase storage будет реализован позже")


def get_video_storage():
    """
    Фабрика для получения экземпляра хранилища видео.
    
    Использует конфигурацию из переменных окружения:
    - VIDEO_STORAGE_TYPE: 'local' или 'supabase' (по умолчанию 'local')
    - Для local: VIDEO_STORAGE_PATH, VIDEO_BASE_URL
    - Для supabase: SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET
    
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
        return SupabaseVideoStorage(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_KEY'),
            bucket_name=os.getenv('SUPABASE_BUCKET', 'signs')
        )
    else:
        raise ValueError(f"Неизвестный тип хранилища: {storage_type}")

