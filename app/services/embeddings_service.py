"""
Сервис для работы с embeddings жестов.
Инкапсулирует всю логику генерации и валидации embeddings.
"""
from typing import Optional, List
from flask import current_app

from app.utils.embeddings import get_embedding_generator
from app.utils.validators import validate_embeddings


class EmbeddingsService:
    """Сервис для работы с embeddings жестов."""
    
    @staticmethod
    def generate_for_sign(word: str, description: Optional[str] = None) -> Optional[List[float]]:
        """
        Генерация embeddings для жеста.
        
        Args:
            word: Слово жеста
            description: Описание жеста (опционально)
            
        Returns:
            Список embeddings или None при ошибке
        """
        generator = get_embedding_generator()
        if not generator:
            current_app.logger.warning("Генерация embeddings пропущена: модель не загружена")
            return None
        
        try:
            embeddings = generator.generate(word, description)
            if validate_embeddings(embeddings):
                return embeddings
            else:
                current_app.logger.warning(f"Невалидные embeddings для слова '{word}'")
                return None
        except Exception as e:
            current_app.logger.error(f"Ошибка генерации embeddings: {e}")
            return None
    
    @staticmethod
    def is_generator_available() -> bool:
        """
        Проверка доступности генератора embeddings.
        
        Returns:
            True если генератор доступен, False иначе
        """
        return get_embedding_generator() is not None
    
    @staticmethod
    def regenerate_for_sign(sign) -> Optional[List[float]]:
        """
        Перегенерация embeddings для существующего жеста.
        
        Args:
            sign: Объект жеста (должен иметь атрибуты word и description)
            
        Returns:
            Список embeddings или None при ошибке
        """
        return EmbeddingsService.generate_for_sign(sign.word, sign.description)
    
    @staticmethod
    def generate_for_text(text: str) -> Optional[List[float]]:
        """
        Генерация embeddings для произвольного текста (например, поискового запроса).
        
        Args:
            text: Текст для генерации embeddings
            
        Returns:
            Список embeddings или None при ошибке
        """
        generator = get_embedding_generator()
        if not generator:
            current_app.logger.warning("Генерация embeddings пропущена: модель не загружена")
            return None
        
        try:
            embeddings = generator.generate(text, None)
            if validate_embeddings(embeddings):
                return embeddings
            else:
                current_app.logger.warning(f"Невалидные embeddings для текста '{text[:50]}...'")
                return None
        except Exception as e:
            current_app.logger.error(f"Ошибка генерации embeddings для текста: {e}")
            return None

