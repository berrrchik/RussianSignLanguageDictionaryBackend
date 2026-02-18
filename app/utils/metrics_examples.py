"""
Примеры использования метрик в коде приложения.

Этот файл содержит примеры кода для добавления метрик в различные endpoints.
Скопируйте нужные примеры в соответствующие файлы routes.
"""

# ============================================================================
# ПРИМЕР 1: Использование метрик синхронизации в app/routes/sync.py
# ============================================================================

"""
# В начале файла добавьте импорты:
from app.utils.metrics import (
    sync_check_total,
    sync_data_total,
    sync_data_size,
    sync_duration
)
from app.utils.logging_config import get_logger, log_business_event

logger = get_logger(__name__)

# В функции check_updates_raw:
@bp.route('/check', methods=['GET'])
def check_updates_raw():
    # ... существующий код получения client_timestamp ...
    
    # Добавляем метрику и логирование
    sync_check_total.labels(has_updates=str(has_updates)).inc()
    
    log_business_event(logger, "Sync check requested", {
        "has_updates": has_updates,
        "last_updated": last_updated,
        "client_timestamp": client_timestamp
    })
    
    return response

# В функции get_sync_data_raw:
@bp.route('/data', methods=['GET'])
def get_sync_data_raw():
    # Используем декоратор для измерения времени
    with sync_duration.time():
        # ... существующий код получения данных ...
        
        categories = [CategoryRawResponse(...) for ...]
        signs = [SignRawResponse(...) for ...]
        lessons = [LessonRawResponse(...) for ...]
        
        # Добавляем метрики
        sync_data_total.inc()
        sync_data_size.labels(data_type='categories').observe(len(categories))
        sync_data_size.labels(data_type='signs').observe(len(signs))
        sync_data_size.labels(data_type='lessons').observe(len(lessons))
        
        log_business_event(logger, "Full sync completed", {
            "categories_count": len(categories),
            "signs_count": len(signs),
            "lessons_count": len(lessons)
        })
        
        return response
"""

# ============================================================================
# ПРИМЕР 2: Использование метрик поиска в app/routes/search.py
# ============================================================================

"""
# В начале файла добавьте импорты:
from app.utils.metrics import (
    search_requests_total,
    search_duration,
    search_results_count,
    search_avg_similarity,
    search_empty_results
)
from app.utils.logging_config import get_logger, log_business_event
import time

logger = get_logger(__name__)

# В функции sbert_search:
@bp.route('/sbert', methods=['POST'])
def sbert_search():
    # ... существующий код получения query ...
    
    # Начинаем измерение времени
    start_time = time.time()
    search_requests_total.inc()
    
    try:
        # ... код поиска ...
        results = perform_search(query)
        
        duration = time.time() - start_time
        search_duration.observe(duration)
        
        if results:
            # Вычисляем среднюю релевантность
            avg_sim = sum(r.get('similarity', 0) for r in results) / len(results)
            search_avg_similarity.observe(avg_sim)
            search_results_count.observe(len(results))
            
            log_business_event(logger, "Semantic search performed", {
                "query": query,
                "results_count": len(results),
                "avg_similarity": avg_sim,
                "duration_ms": duration * 1000
            })
        else:
            search_empty_results.inc()
            log_business_event(logger, "Semantic search - no results", {
                "query": query,
                "duration_ms": duration * 1000
            })
        
        return results
        
    except Exception as e:
        # Логируем ошибку
        logger.error(f"Search error: {e}", exc_info=True)
        raise
"""

# ============================================================================
# ПРИМЕР 3: Использование метрик админских операций в app/routes/admin.py
# ============================================================================

"""
# В начале файла добавьте импорты:
from app.utils.metrics import (
    admin_sign_operations,
    admin_category_operations,
    admin_lesson_operations,
    admin_video_uploads,
    admin_video_upload_size,
    admin_auth_attempts,
    admin_active_sessions
)
from app.utils.logging_config import get_logger, log_business_event

logger = get_logger(__name__)

# При создании жеста:
@bp.route('/signs', methods=['POST'])
@admin_required
def create_sign():
    # ... существующий код создания жеста ...
    
    sign = Sign(...)
    db.session.add(sign)
    db.session.commit()
    
    # Добавляем метрику и логирование
    admin_sign_operations.labels(operation='create').inc()
    
    log_business_event(logger, "Sign created", {
        "sign_id": sign.id,
        "word": sign.word,
        "category_id": sign.category_id
    })
    
    return response

# При обновлении жеста:
@bp.route('/signs/<sign_id>', methods=['PUT'])
@admin_required
def update_sign(sign_id):
    # ... существующий код обновления ...
    
    admin_sign_operations.labels(operation='update').inc()
    
    log_business_event(logger, "Sign updated", {
        "sign_id": sign_id
    })
    
    return response

# При удалении жеста:
@bp.route('/signs/<sign_id>', methods=['DELETE'])
@admin_required
def delete_sign(sign_id):
    # ... существующий код удаления ...
    
    admin_sign_operations.labels(operation='delete').inc()
    
    log_business_event(logger, "Sign deleted", {
        "sign_id": sign_id
    })
    
    return response

# При загрузке видео:
@bp.route('/signs/<sign_id>/videos', methods=['POST'])
@admin_required
def upload_video(sign_id):
    # ... существующий код загрузки ...
    
    try:
        file = request.files['video']
        file_size = len(file.read())
        file.seek(0)  # Возвращаемся в начало файла
        
        # ... код сохранения файла ...
        
        admin_video_uploads.labels(status='success').inc()
        admin_video_upload_size.observe(file_size)
        
        log_business_event(logger, "Video uploaded", {
            "sign_id": sign_id,
            "file_size": file_size
        })
        
        return response
        
    except Exception as e:
        admin_video_uploads.labels(status='failure').inc()
        logger.error(f"Video upload error: {e}", exc_info=True)
        raise

# При авторизации:
@bp.route('/auth/login', methods=['POST'])
def login():
    # ... существующий код авторизации ...
    
    if auth_success:
        admin_auth_attempts.labels(status='success').inc()
        admin_active_sessions.inc()
        
        log_business_event(logger, "Admin login successful", {
            "username": username,
            "ip_address": request.remote_addr
        })
    else:
        admin_auth_attempts.labels(status='failure').inc()
        
        log_business_event(logger, "Admin login failed", {
            "username": username,
            "ip_address": request.remote_addr
        })
    
    return response

# При выходе:
@bp.route('/auth/logout', methods=['POST'])
@admin_required
def logout():
    # ... существующий код выхода ...
    
    admin_active_sessions.dec()
    
    return response
"""

# ============================================================================
# ПРИМЕР 4: Использование метрик ML компонентов (SBERT)
# ============================================================================

"""
# В файле, где загружается SBERT модель (например, app/utils/sbert.py):
from app.utils.metrics import (
    sbert_model_status,
    sbert_model_load_duration,
    sbert_embedding_generation_duration,
    sbert_embedding_generation_errors
)
from app.utils.logging_config import get_logger
import time

logger = get_logger(__name__)

# При загрузке модели:
def load_sbert_model():
    start_time = time.time()
    
    try:
        with sbert_model_load_duration.time():
            model = SentenceTransformer('model_name')
        
        sbert_model_status.set(1)  # Модель доступна
        logger.info("SBERT model loaded successfully")
        
        return model
        
    except Exception as e:
        sbert_model_status.set(0)  # Модель недоступна
        logger.error(f"SBERT model load error: {e}", exc_info=True)
        raise

# При генерации embedding:
def generate_embedding(text, model):
    try:
        with sbert_embedding_generation_duration.time():
            embedding = model.encode(text)
        
        return embedding
        
    except Exception as e:
        sbert_embedding_generation_errors.inc()
        logger.error(f"Embedding generation error: {e}", exc_info=True)
        raise
"""

# ============================================================================
# ПРИМЕР 5: Использование метрик базы данных
# ============================================================================

"""
# В файле app/database.py или в middleware:
from app.utils.metrics import (
    db_query_duration,
    db_slow_queries,
    db_connection_errors
)
from app.utils.logging_config import get_logger
import time

logger = get_logger(__name__)

# Middleware для отслеживания SQL запросов:
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    
    # Определяем тип операции
    operation = statement.strip().split()[0].upper()
    if operation in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
        db_query_duration.labels(operation=operation).observe(total)
        
        # Отслеживаем медленные запросы
        if total > 1.0:
            db_slow_queries.labels(threshold='>1s').inc()
            logger.warning(f"Slow query (>1s): {statement[:100]}...", extra={
                'extra_data': {'duration': total, 'operation': operation}
            })
        elif total > 0.5:
            db_slow_queries.labels(threshold='>500ms').inc()
        elif total > 0.1:
            db_slow_queries.labels(threshold='>100ms').inc()

# При ошибках подключения:
def handle_db_connection_error():
    db_connection_errors.inc()
    logger.error("Database connection error", exc_info=True)
"""

# ============================================================================
# ПРИМЕР 6: Обновление метрик контента
# ============================================================================

"""
# В файле, где обновляется контент (например, при запуске или по расписанию):
from app.utils.metrics import (
    content_signs_total,
    content_signs_with_videos,
    content_categories_total,
    content_lessons_total
)
from app.models.sign import Sign
from app.models.category import Category
from app.models.lesson import Lesson
from app.database import db

def update_content_metrics():
    # Общее количество жестов
    total_signs = db.session.query(func.count(Sign.id)).scalar()
    content_signs_total.set(total_signs)
    
    # Жесты с видео
    signs_with_videos = db.session.query(func.count(Sign.id)).join(
        Sign.videos
    ).group_by(Sign.id).count()
    content_signs_with_videos.set(signs_with_videos)
    
    # Количество категорий
    total_categories = db.session.query(func.count(Category.id)).scalar()
    content_categories_total.set(total_categories)
    
    # Количество уроков
    total_lessons = db.session.query(func.count(Lesson.id)).scalar()
    content_lessons_total.set(total_lessons)

# Вызывайте эту функцию:
# - При запуске приложения (в create_app)
# - По расписанию (через cron или scheduler)
# - После операций создания/удаления контента
"""
