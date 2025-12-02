"""
Генерация embeddings для жестов с помощью модели RuBERT.
"""
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_embedding_generator = None


class EmbeddingGenerator:
    """Класс для генерации векторных представлений текста."""
    
    def __init__(self):
        """Инициализация с загрузкой модели RuBERT."""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            logger.info("Загрузка модели RuBERT...")
            self.tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased")
            self.model = AutoModel.from_pretrained("DeepPavlov/rubert-base-cased")
            self.model.eval()  # Режим инференса
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            logger.info(f"Модель RuBERT загружена на {self.device}")
        except Exception as e:
            logger.critical(f"Не удалось загрузить модель RuBERT: {e}")
            raise
    
    def generate(self, word: str, description: Optional[str] = None) -> List[float]:
        """
        Генерация векторного представления текста жеста.
        
        Args:
            word: Слово жеста
            description: Описание жеста (опционально)
            
        Returns:
            Список из 768 чисел (embeddings)
        """
        import torch
        import numpy as np
        
        start_time = time.time()
        
        # Объединение текста
        text = word
        if description:
            text += " " + description
        
        # Токенизация
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Генерация embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Берем embedding для [CLS] токена (индекс 0)
            embedding = outputs.last_hidden_state[0][0].cpu().numpy().tolist()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Генерация embeddings заняла {elapsed_time:.3f} секунд")
        
        return embedding


def get_embedding_generator() -> Optional[EmbeddingGenerator]:
    """
    Получение singleton экземпляра EmbeddingGenerator.
    
    Returns:
        Экземпляр EmbeddingGenerator или None если модель не загружена
    """
    global _embedding_generator
    
    if _embedding_generator is None:
        try:
            _embedding_generator = EmbeddingGenerator()
        except Exception as e:
            logger.critical(f"Не удалось загрузить модель RuBERT: {e}")
            return None
    
    return _embedding_generator

