# PromQL запросы для Grafana дашбордов

Этот файл содержит готовые PromQL запросы для создания панелей в Grafana.

## HTTP метрики (Flask)

### Количество запросов по методам
```promql
sum(rate(flask_http_request_total[5m])) by (method)
```

### Количество запросов по путям
```promql
sum(rate(flask_http_request_total[5m])) by (path)
```

### Количество запросов по методам и путям
```promql
sum(rate(flask_http_request_total[5m])) by (method, path)
```

### HTTP статус коды
```promql
sum(rate(flask_http_request_total[5m])) by (status)
```

### Ошибки (4xx, 5xx)
```promql
# 4xx ошибки
sum(rate(flask_http_request_total{status=~"4.."}[5m]))

# 5xx ошибки
sum(rate(flask_http_request_total{status=~"5.."}[5m]))
```

### Время ответа (перцентили)
```promql
# p50
histogram_quantile(0.50, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le))

# p95
histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le))

# p99
histogram_quantile(0.99, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le))
```

### Время ответа по путям (p95)
```promql
histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le, path))
```

### Активные запросы
```promql
flask_http_request_active
```

### Размер ответов
```promql
sum(rate(flask_http_request_bytes_bucket[5m])) by (le)
```

---

## Метрики синхронизации

### Количество проверок синхронизации
```promql
sum(rate(sign_language_sync_check_total[5m])) by (has_updates)
```

### Количество полных синхронизаций
```promql
sum(rate(sign_language_sync_data_total[5m]))
```

### Размер данных синхронизации
```promql
# Средний размер по типам данных
sum(rate(sign_language_sync_data_size_bucket[5m])) by (data_type, le)
```

### Длительность синхронизации
```promql
# p95
histogram_quantile(0.95, sum(rate(sign_language_sync_duration_seconds_bucket[5m])) by (le))

# p50
histogram_quantile(0.50, sum(rate(sign_language_sync_duration_seconds_bucket[5m])) by (le))
```

---

## Метрики поиска

### Количество поисковых запросов
```promql
sum(rate(sign_language_search_requests_total[5m]))
```

### Длительность поиска
```promql
# p95
histogram_quantile(0.95, sum(rate(sign_language_search_duration_seconds_bucket[5m])) by (le))

# p50
histogram_quantile(0.50, sum(rate(sign_language_search_duration_seconds_bucket[5m])) by (le))
```

### Количество результатов поиска
```promql
# Среднее количество результатов
histogram_quantile(0.50, sum(rate(sign_language_search_results_count_bucket[5m])) by (le))

# Максимальное количество результатов
histogram_quantile(0.95, sum(rate(sign_language_search_results_count_bucket[5m])) by (le))
```

### Средняя релевантность результатов
```promql
histogram_quantile(0.50, sum(rate(sign_language_search_avg_similarity_bucket[5m])) by (le))
```

### Поиски без результатов
```promql
sum(rate(sign_language_search_empty_results_total[5m]))
```

---

## Метрики административных операций

### Операции с жестами
```promql
sum(rate(sign_language_admin_sign_operations_total[5m])) by (operation)
```

### Операции с категориями
```promql
sum(rate(sign_language_admin_category_operations_total[5m])) by (operation)
```

### Операции с уроками
```promql
sum(rate(sign_language_admin_lesson_operations_total[5m])) by (operation)
```

### Загрузки видео
```promql
sum(rate(sign_language_admin_video_uploads_total[5m])) by (status)
```

### Размер загружаемых видео
```promql
histogram_quantile(0.95, sum(rate(sign_language_admin_video_upload_size_bytes_bucket[5m])) by (le))
```

### Попытки авторизации
```promql
sum(rate(sign_language_admin_auth_attempts_total[5m])) by (status)
```

### Активные сессии администраторов
```promql
sign_language_admin_active_sessions
```

---

## Метрики ML компонентов (SBERT)

### Статус модели
```promql
sign_language_sbert_model_status
```

### Время загрузки модели
```promql
histogram_quantile(0.95, sum(rate(sign_language_sbert_model_load_duration_seconds_bucket[5m])) by (le))
```

### Время генерации embedding
```promql
# p95
histogram_quantile(0.95, sum(rate(sign_language_sbert_embedding_generation_duration_seconds_bucket[5m])) by (le))

# p50
histogram_quantile(0.50, sum(rate(sign_language_sbert_embedding_generation_duration_seconds_bucket[5m])) by (le))
```

### Ошибки генерации embedding
```promql
sum(rate(sign_language_sbert_embedding_generation_errors_total[5m]))
```

---

## Метрики базы данных

### Длительность запросов
```promql
# p95 по типам операций
histogram_quantile(0.95, sum(rate(sign_language_db_query_duration_seconds_bucket[5m])) by (le, operation))
```

### Медленные запросы
```promql
# >100ms
sum(rate(sign_language_db_slow_queries_total{threshold=">100ms"}[5m]))

# >500ms
sum(rate(sign_language_db_slow_queries_total{threshold=">500ms"}[5m]))

# >1s
sum(rate(sign_language_db_slow_queries_total{threshold=">1s"}[5m]))
```

### Ошибки подключения к БД
```promql
sum(rate(sign_language_db_connection_errors_total[5m]))
```

---

## Метрики контента

### Общее количество жестов
```promql
sign_language_content_signs_total
```

### Жесты с видео
```promql
sign_language_content_signs_with_videos_total
```

### Количество категорий
```promql
sign_language_content_categories_total
```

### Количество уроков
```promql
sign_language_content_lessons_total
```

---

## Loki запросы (логи)

### Все логи приложения
```logql
{job="sign-language-backend"}
```

### Логи по уровню
```logql
{job="sign-language-backend"} |= "ERROR"
{job="sign-language-backend"} |= "WARNING"
{job="sign-language-backend"} |= "INFO"
```

### Логи с ошибками
```logql
{job="sign-language-backend"} |= "ERROR" or |= "CRITICAL"
```

### Медленные запросы (>500ms)
```logql
{job="sign-language-backend"} | json | duration_ms > 500
```

### Запросы по статус коду
```logql
{job="sign-language-backend"} | json | status_code=~"[45].."
```

### Запросы по пути
```logql
{job="sign-language-backend"} | json | path="/api/v1/sync/check"
```

### Количество логов по уровню
```logql
sum(count_over_time({job="sign-language-backend"} |= "level" | json | level=~"ERROR|WARNING|INFO"[5m])) by (level)
```

### Количество ошибок по времени
```logql
sum(count_over_time({job="sign-language-backend"} |= "ERROR"[5m]))
```

---

## Комбинированные запросы

### Процент успешных запросов
```promql
sum(rate(flask_http_request_total{status=~"2.."}[5m])) / sum(rate(flask_http_request_total[5m])) * 100
```

### Процент запросов обработанных за <100ms
```promql
sum(rate(flask_http_request_duration_seconds_bucket{le="0.1"}[5m])) / sum(rate(flask_http_request_duration_seconds_count[5m])) * 100
```

### Процент запросов обработанных за <500ms
```promql
sum(rate(flask_http_request_duration_seconds_bucket{le="0.5"}[5m])) / sum(rate(flask_http_request_duration_seconds_count[5m])) * 100
```

### Процент запросов обработанных за <1s
```promql
sum(rate(flask_http_request_duration_seconds_bucket{le="1.0"}[5m])) / sum(rate(flask_http_request_duration_seconds_count[5m])) * 100
```

### Топ-10 самых используемых эндпоинтов
```promql
topk(10, sum(rate(flask_http_request_total[5m])) by (path))
```

### Процент поисков с результатами
```promql
(1 - sum(rate(sign_language_search_empty_results_total[5m])) / sum(rate(sign_language_search_requests_total[5m]))) * 100
```
