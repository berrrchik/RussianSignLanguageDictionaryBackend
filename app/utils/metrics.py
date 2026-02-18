"""
Кастомные метрики для бизнес-логики приложения.

Этот модуль экспортирует Prometheus метрики для отслеживания:
- Синхронизации мобильных клиентов
- Семантического поиска
- Административных операций
- ML компонентов (SBERT)
"""
try:
    from prometheus_client import Counter, Histogram, Gauge
except ImportError:
    # Если prometheus_client не установлен, создаём заглушки
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def inc(self, value=1):
            pass
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def observe(self, value):
            pass
        def time(self):
            import time
            class Timer:
                def __enter__(self):
                    self.start = time.time()
                    return self
                def __exit__(self, *args):
                    pass
            return Timer()
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def set(self, value):
            pass
        def inc(self, value=1):
            pass
        def dec(self, value=1):
            pass


# ============================================================================
# Метрики синхронизации мобильных клиентов
# ============================================================================

sync_check_total = Counter(
    'sign_language_sync_check_total',
    'Total number of sync check requests',
    ['has_updates']
)

sync_data_total = Counter(
    'sign_language_sync_data_total',
    'Total number of full sync requests'
)

sync_data_size = Histogram(
    'sign_language_sync_data_size',
    'Size of sync data (number of items)',
    ['data_type'],  # categories, signs, lessons
    buckets=[10, 50, 100, 500, 1000, 5000, 10000]
)

sync_duration = Histogram(
    'sign_language_sync_duration_seconds',
    'Sync request duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)


# ============================================================================
# Метрики семантического поиска
# ============================================================================

search_requests_total = Counter(
    'sign_language_search_requests_total',
    'Total number of search requests'
)

search_duration = Histogram(
    'sign_language_search_duration_seconds',
    'Search request duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

search_results_count = Histogram(
    'sign_language_search_results_count',
    'Number of search results returned',
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

search_avg_similarity = Histogram(
    'sign_language_search_avg_similarity',
    'Average similarity score of search results',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

search_empty_results = Counter(
    'sign_language_search_empty_results_total',
    'Total number of searches with no results'
)


# ============================================================================
# Метрики административных операций
# ============================================================================

admin_sign_operations = Counter(
    'sign_language_admin_sign_operations_total',
    'Total admin sign operations',
    ['operation']  # create, update, delete
)

admin_category_operations = Counter(
    'sign_language_admin_category_operations_total',
    'Total admin category operations',
    ['operation']  # create, update, delete
)

admin_lesson_operations = Counter(
    'sign_language_admin_lesson_operations_total',
    'Total admin lesson operations',
    ['operation']  # create, update, delete
)

admin_video_uploads = Counter(
    'sign_language_admin_video_uploads_total',
    'Total video uploads',
    ['status']  # success, failure
)

admin_video_upload_size = Histogram(
    'sign_language_admin_video_upload_size_bytes',
    'Size of uploaded video files',
    buckets=[1024*1024, 5*1024*1024, 10*1024*1024, 20*1024*1024, 50*1024*1024]  # 1MB, 5MB, 10MB, 20MB, 50MB
)

admin_auth_attempts = Counter(
    'sign_language_admin_auth_attempts_total',
    'Total admin authentication attempts',
    ['status']  # success, failure
)

admin_active_sessions = Gauge(
    'sign_language_admin_active_sessions',
    'Number of active admin sessions'
)


# ============================================================================
# Метрики ML компонентов (SBERT)
# ============================================================================

sbert_model_status = Gauge(
    'sign_language_sbert_model_status',
    'SBERT model status (1 = available, 0 = unavailable)'
)

sbert_model_load_duration = Histogram(
    'sign_language_sbert_model_load_duration_seconds',
    'Time taken to load SBERT model',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
)

sbert_embedding_generation_duration = Histogram(
    'sign_language_sbert_embedding_generation_duration_seconds',
    'Time taken to generate embedding',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

sbert_embedding_generation_errors = Counter(
    'sign_language_sbert_embedding_generation_errors_total',
    'Total number of embedding generation errors'
)


# ============================================================================
# Метрики базы данных (SQLAlchemy)
# ============================================================================

db_query_duration = Histogram(
    'sign_language_db_query_duration_seconds',
    'Database query duration',
    ['operation'],  # select, insert, update, delete
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

db_slow_queries = Counter(
    'sign_language_db_slow_queries_total',
    'Total number of slow queries',
    ['threshold']  # >100ms, >500ms, >1s
)

db_connection_errors = Counter(
    'sign_language_db_connection_errors_total',
    'Total number of database connection errors'
)


# ============================================================================
# Метрики контента
# ============================================================================

content_signs_total = Gauge(
    'sign_language_content_signs_total',
    'Total number of signs in database'
)

content_signs_with_videos = Gauge(
    'sign_language_content_signs_with_videos_total',
    'Number of signs with videos'
)

content_categories_total = Gauge(
    'sign_language_content_categories_total',
    'Total number of categories'
)

content_lessons_total = Gauge(
    'sign_language_content_lessons_total',
    'Total number of lessons'
)
