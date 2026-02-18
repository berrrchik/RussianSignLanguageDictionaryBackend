# 📊 Руководство по дашбордам Grafana

Это руководство поможет вам импортировать и настроить готовые дашборды для мониторинга приложения.

## 📁 Структура файлов

```
grafana/
├── dashboards/
│   ├── application-overview.json      # Обзор приложения (HTTP метрики)
│   ├── business-metrics.json          # Бизнес-метрики (sync, search, admin)
│   ├── application-logs.json          # Логи приложения
│   └── promql-queries.md              # Готовые PromQL запросы
└── GRAFANA_DASHBOARDS_GUIDE.md        # Этот файл
```

---

## 🚀 Импорт дашбордов

### Способ 1: Импорт через веб-интерфейс Grafana

1. **Откройте Grafana:**
   ```
   http://93.77.186.203:3000
   ```

2. **Перейдите в раздел дашбордов:**
   - Нажмите на иконку **Dashboards** (четыре квадрата) в левом меню
   - Нажмите **Import**

3. **Импортируйте дашборд:**
   - Нажмите **Upload JSON file**
   - Выберите файл из директории `grafana/dashboards/`
   - Или вставьте содержимое JSON файла в текстовое поле
   - Нажмите **Load**

4. **Настройте источники данных:**
   - Выберите **Prometheus** как источник для метрик
   - Выберите **Loki** как источник для логов
   - Нажмите **Import**

### Способ 2: Импорт через API (для автоматизации)

```bash
# На сервере
cd /Users/anastasiabercik/PycharmProjects/SignLanguageDictionaryBackend

# Импорт дашборда "Application Overview"
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/dashboards/application-overview.json

# Импорт дашборда "Business Metrics"
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/dashboards/business-metrics.json

# Импорт дашборда "Application Logs"
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/dashboards/application-logs.json
```

**Примечание:** Замените `admin:admin` на ваши учётные данные Grafana.

---

## 📊 Описание дашбордов

### 1. Application Overview

**Файл:** `application-overview.json`

**Содержит:**
- HTTP Requests Rate - количество запросов в секунду по методам и путям
- HTTP Status Codes - распределение статус кодов (pie chart)
- Response Time (p95) - время ответа по путям
- Response Time (p50, p95, p99) - перцентили времени ответа
- Error Rate (4xx, 5xx) - частота ошибок
- Active Requests - количество активных запросов

**Источник данных:** Prometheus

---

### 2. Business Metrics

**Файл:** `business-metrics.json`

**Содержит:**
- Sync Check Requests - количество проверок синхронизации
- Full Sync Requests - количество полных синхронизаций
- Sync Data Size - размер данных синхронизации
- Search Requests - количество поисковых запросов
- Search Duration - время выполнения поиска
- Search Results Count - количество результатов поиска
- Search Empty Results - поиски без результатов
- Admin Operations - операции с жестами, категориями, уроками
- Video Uploads - загрузки видео
- Admin Auth Attempts - попытки авторизации
- Active Admin Sessions - активные сессии администраторов

**Источник данных:** Prometheus

**Примечание:** Для работы этого дашборда нужно добавить использование метрик в код (см. раздел "Использование метрик в коде").

---

### 3. Application Logs

**Файл:** `application-logs.json`

**Содержит:**
- Logs Explorer - просмотр всех логов
- Logs by Level - количество логов по уровням (ERROR, WARNING, INFO)
- Error Logs - фильтр только ошибок
- Slow Requests (>500ms) - медленные запросы
- HTTP Status Codes from Logs - статус коды из логов

**Источник данных:** Loki

---

## 💻 Использование метрик в коде

Для того чтобы дашборды отображали данные, нужно добавить использование метрик в код приложения.

### Пример: Добавление метрик синхронизации

Откройте файл `app/routes/sync.py` и добавьте:

```python
from app.utils.metrics import (
    sync_check_total,
    sync_data_total,
    sync_data_size,
    sync_duration
)

# В функции check_updates_raw:
@sync_duration.time()
def check_updates_raw():
    # ... существующий код ...
    
    # Добавляем метрику
    sync_check_total.labels(has_updates=str(has_updates)).inc()
    
    return response

# В функции get_sync_data_raw:
@sync_duration.time()
def get_sync_data_raw():
    # ... существующий код получения данных ...
    
    # Добавляем метрики
    sync_data_total.inc()
    sync_data_size.labels(data_type='categories').observe(len(categories))
    sync_data_size.labels(data_type='signs').observe(len(signs))
    sync_data_size.labels(data_type='lessons').observe(len(lessons))
    
    return response
```

### Пример: Добавление метрик поиска

Откройте файл `app/routes/search.py` и добавьте:

```python
from app.utils.metrics import (
    search_requests_total,
    search_duration,
    search_results_count,
    search_avg_similarity,
    search_empty_results
)

# В функции sbert_search:
def sbert_search():
    search_requests_total.inc()
    
    start_time = time.time()
    # ... код поиска ...
    duration = time.time() - start_time
    
    if results:
        avg_sim = sum(r['similarity'] for r in results) / len(results)
        search_avg_similarity.observe(avg_sim)
        search_results_count.observe(len(results))
    else:
        search_empty_results.inc()
    
    search_duration.observe(duration)
    
    return results
```

### Пример: Добавление метрик админских операций

Откройте файл `app/routes/admin.py` и добавьте:

```python
from app.utils.metrics import (
    admin_sign_operations,
    admin_video_uploads,
    admin_auth_attempts,
    admin_active_sessions
)

# При создании жеста:
admin_sign_operations.labels(operation='create').inc()

# При обновлении жеста:
admin_sign_operations.labels(operation='update').inc()

# При удалении жеста:
admin_sign_operations.labels(operation='delete').inc()

# При загрузке видео:
try:
    # ... код загрузки ...
    admin_video_uploads.labels(status='success').inc()
except Exception:
    admin_video_uploads.labels(status='failure').inc()

# При авторизации:
if auth_success:
    admin_auth_attempts.labels(status='success').inc()
    admin_active_sessions.inc()
else:
    admin_auth_attempts.labels(status='failure').inc()
```

---

## 🔧 Создание собственных панелей

Если вы хотите создать свои панели, используйте готовые PromQL запросы из файла `promql-queries.md`.

### Пример создания панели "Топ-10 эндпоинтов"

1. В Grafana: **Dashboards** → выберите дашборд → **Add panel**
2. Выберите источник данных **Prometheus**
3. В поле запроса вставьте:
   ```promql
   topk(10, sum(rate(flask_http_request_total[5m])) by (path))
   ```
4. Настройте визуализацию (график, таблица и т.д.)
5. Сохраните панель

---

## 📝 Настройка алертов (опционально)

Вы можете создать алерты на основе метрик. Например:

### Алерт на высокую частоту ошибок

1. В панели с метрикой ошибок нажмите **Edit**
2. Перейдите на вкладку **Alert**
3. Создайте правило:
   - **Condition:** `WHEN avg() OF query(A, 5m, now) IS ABOVE 10`
   - **Message:** "Высокая частота ошибок: {{ $value }} ошибок/сек"

### Алерт на медленные запросы

1. Создайте панель с метрикой времени ответа
2. Создайте алерт:
   - **Condition:** `WHEN avg() OF query(A, 5m, now) IS ABOVE 1`
   - **Message:** "Медленные запросы: p95 = {{ $value }}s"

---

## 🔍 Отладка дашбордов

### Проблема: Панели не отображают данные

1. **Проверьте источники данных:**
   - Убедитесь, что Prometheus и Loki настроены и работают
   - Проверьте доступность: `curl http://localhost:9090/api/v1/targets`

2. **Проверьте метрики:**
   ```bash
   curl http://localhost:5001/metrics | grep sign_language
   ```

3. **Проверьте логи:**
   ```bash
   tail -f /var/log/app/application.log | jq
   ```

4. **Проверьте запросы в Grafana:**
   - Откройте панель в режиме редактирования
   - Нажмите **Query Inspector**
   - Проверьте, возвращает ли запрос данные

### Проблема: Метрики не собираются

1. **Убедитесь, что метрики используются в коде:**
   - Проверьте, что вы добавили использование метрик в endpoints
   - Перезапустите приложение

2. **Проверьте, что Prometheus собирает метрики:**
   - Откройте `http://93.77.186.203:9090/targets`
   - Убедитесь, что target `flask-app` в состоянии "UP"

---

## 📚 Дополнительные ресурсы

- [PromQL запросы](dashboards/promql-queries.md) - готовые запросы для панелей
- [MONITORING_SETUP_GUIDE.md](../../MONITORING_SETUP_GUIDE.md) - полная инструкция по настройке
- [Grafana документация](https://grafana.com/docs/grafana/latest/) - официальная документация

---

**Последнее обновление:** 2025-02-17
