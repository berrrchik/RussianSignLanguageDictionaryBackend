"""
Сервис семантического поиска на основе SentenceTransformer (SBERT).

Использует модель ai-forever/sbert_large_nlu_ru для генерации embeddings
и поиска похожих жестов в базе данных.
"""
from functools import cached_property
from typing import List, Tuple, Optional, TYPE_CHECKING
import logging

from flask import current_app

if TYPE_CHECKING:
    from numpy import ndarray
    from sentence_transformers import SentenceTransformer
    from sentence_transformers import util as sbert_util
else:
    try:
        from numpy import ndarray
        from sentence_transformers import SentenceTransformer, util as sbert_util
    except ImportError:
        # Если sentence-transformers не установлен, импорт будет отложен
        ndarray = None
        SentenceTransformer = None
        sbert_util = None

from app.database import db
from app.models.sign import Sign

logger = logging.getLogger(__name__)


class SBERTSearchService:
    """
    Сервис для семантического поиска жестов с использованием SentenceTransformer.
    
    Загружает слова из базы данных и использует SBERT модель для генерации
    embeddings и поиска похожих жестов.
    """
    
    def __init__(
        self,
        model_path: str = "ai-forever/sbert_large_nlu_ru",
        device: Optional[str] = None
    ):
        """
        Инициализация сервиса поиска.
        
        Args:
            model_path: Путь к модели SentenceTransformer или имя модели на HuggingFace
            device: Устройство для вычислений ('cpu', 'cuda', 'mps'). Если None, определяется автоматически
        """
        self.model_path = model_path
        self.device = device or self._detect_device()
        
        # Инициализация модели и загрузка данных
        logger.info(f"Инициализация SBERTSearchService с моделью: {model_path}")
        _ = self.model  # Загрузка модели
        _ = self.embeddings  # Загрузка embeddings
        logger.info("SBERTSearchService инициализирован")
    
    def _detect_device(self) -> str:
        """Автоматическое определение устройства для вычислений."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        except ImportError:
            return "cpu"
    
    @cached_property
    def model(self) -> SentenceTransformer:
        """Загрузка модели SentenceTransformer."""
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers не установлен. "
                "Установите: pip install sentence-transformers"
            )
        
        logger.info(f"Загрузка модели SentenceTransformer: {self.model_path}")
        try:
            model = SentenceTransformer(
                self.model_path,
                device=self.device
            )
            logger.info(f"Модель загружена на устройство: {self.device}")
            return model
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise
    
    @cached_property
    def words(self) -> List[str]:
        """
        Загрузка слов из базы данных.
        
        Returns:
            Список слов всех жестов из базы данных
        """
        logger.info("Загрузка слов из базы данных...")
        try:
            with db.session.begin():
                signs = db.session.query(Sign.word).order_by(Sign.word).all()
                words = [sign.word for sign in signs]
            
            logger.info(f"Загружено {len(words)} слов из базы данных")
            return words
        except Exception as e:
            logger.error(f"Ошибка загрузки слов из базы данных: {e}")
            raise
    
    @cached_property
    def sign_ids(self) -> List[str]:
        """
        Загрузка ID жестов из базы данных.
        
        Returns:
            Список ID жестов, соответствующих словам (в том же порядке, что и words)
        """
        logger.info("Загрузка ID жестов из базы данных...")
        try:
            with db.session.begin():
                signs = db.session.query(Sign.id, Sign.word).order_by(Sign.word).all()
                sign_ids = [sign.id for sign in signs]
            
            logger.info(f"Загружено {len(sign_ids)} ID жестов")
            return sign_ids
        except Exception as e:
            logger.error(f"Ошибка загрузки ID жестов из базы данных: {e}")
            raise
    
    @cached_property
    def embeddings(self):
        """
        Генерация embeddings для всех слов из базы данных.
        
        Returns:
            Массив embeddings (n_words, embedding_dim)
        """
        if sbert_util is None:
            raise ImportError(
                "sentence-transformers не установлен. "
                "Установите: pip install sentence-transformers"
            )
        
        logger.info("Генерация embeddings для всех слов...")
        try:
            words = self.words
            embeddings = self.model.encode(
                words,
                normalize_embeddings=True,
                show_progress_bar=True,
                batch_size=32
            )
            logger.info(f"Сгенерировано embeddings: {embeddings.shape}")
            return embeddings
        except Exception as e:
            logger.error(f"Ошибка генерации embeddings: {e}")
            raise
    
    def search(
        self,
        search_query: str,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Tuple[str, str, float]]:
        """
        Поиск похожих жестов по текстовому запросу.
        
        Args:
            search_query: Текстовый запрос для поиска
            limit: Максимальное количество результатов
            min_similarity: Минимальное значение сходства (0-1)
            
        Returns:
            Список кортежей (sign_id, word, similarity), отсортированных по убыванию сходства
        """
        if not search_query or not search_query.strip():
            return []
        
        try:
            if sbert_util is None:
                raise ImportError(
                    "sentence-transformers не установлен. "
                    "Установите: pip install sentence-transformers"
                )
            
            # Генерация embedding для запроса
            query_embedding = self.model.encode(
                search_query,
                normalize_embeddings=True
            )
            
            # Вычисление косинусного сходства
            scores = sbert_util.cos_sim(query_embedding, self.embeddings)[0]
            
            # Получение ID жестов
            sign_ids = self.sign_ids
            
            # Создание списка результатов
            results = []
            for i, (word, score) in enumerate(zip(self.words, scores)):
                if score >= min_similarity:
                    sign_id = sign_ids[i]
                    results.append((sign_id, word, float(score)))
            
            # Сортировка по убыванию сходства
            results.sort(key=lambda x: x[2], reverse=True)
            
            # Ограничение количества результатов
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []
    
    def __call__(
        self,
        search_query: str,
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[str]:
        """
        Удобный интерфейс для поиска (возвращает только слова).
        
        Args:
            search_query: Текстовый запрос для поиска
            limit: Максимальное количество результатов
            min_similarity: Минимальное значение сходства (0-1)
            
        Returns:
            Список слов, отсортированных по убыванию сходства
        """
        results = self.search(search_query, limit, min_similarity)
        return [word for _, word, _ in results]
    
    def invalidate_cache(self):
        """Сброс кеша для перезагрузки данных из базы."""
        # Удаление cached_property
        for attr in ['words', 'sign_ids', 'embeddings', 'model']:
            if hasattr(self.__class__, attr):
                if attr in self.__dict__:
                    delattr(self, attr)


# Singleton экземпляр сервиса
_sbert_search_service: Optional[SBERTSearchService] = None


def get_sbert_search_service(
    model_path: str = "ai-forever/sbert_large_nlu_ru",
    device: Optional[str] = None,
    force_reload: bool = False
) -> SBERTSearchService:
    """
    Получение singleton экземпляра SBERTSearchService.
    
    Args:
        model_path: Путь к модели SentenceTransformer
        device: Устройство для вычислений
        force_reload: Принудительная перезагрузка сервиса
        
    Returns:
        Экземпляр SBERTSearchService
    """
    global _sbert_search_service
    
    if _sbert_search_service is None or force_reload:
        _sbert_search_service = SBERTSearchService(
            model_path=model_path,
            device=device
        )
    
    return _sbert_search_service
