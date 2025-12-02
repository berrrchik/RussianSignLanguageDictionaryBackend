# Словарь русского жестового языка - Backend

Backend-система для управления словарём русского жестового языка для Всероссийского общества глухих (ВОГ). Система предоставляет REST API для мобильного iOS приложения и веб-административную панель для управления контентом.

## Быстрый старт

### Предварительные требования

- Python 3.10+
- PostgreSQL 17+ (совместимо с 14+)
- pip (менеджер пакетов Python)

### Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone git@github.com:berrrchik/RussianSignLanguageDictionaryBackend.git
   cd RussianSignLanguageDictionaryBackend
   ```

2. **Создайте виртуальное окружение:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # или
   venv\Scripts\activate     # Windows
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте базу данных:**
   ```bash
   # Создайте базу данных PostgreSQL
   createdb sign_language_dict
   
   # Примените схему
   psql -U postgres -d sign_language_dict -f database/init_schema.sql
   ```

5. **Создайте файл `.env`:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env и заполните реальными значениями
   ```
   
   Минимальная конфигурация для разработки:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sign_language_dict
   JWT_SECRET_KEY=change-me-in-production-generate-random-string
   FLASK_DEBUG=True
   FLASK_ENV=development
   FLASK_PORT=5001
   ```
   
   Полный список переменных см. в `.env.example`

6. **Создайте администратора:**
   ```bash
   python scripts/create_admin_simple.py --username admin --password your_password
   ```

7. **Запустите приложение:**
   ```bash
   python run.py
   ```

Приложение будет доступно по адресу: `http://localhost:5001`

## Основные возможности

### REST API
- **Синхронизация данных** для мобильного приложения
- **CRUD операции** для жестов, категорий, видео и синонимов
- **Автоматическая генерация embeddings** для семантического поиска
- **JWT авторизация** для административных endpoints

### Веб-административная панель
- Управление жестами (создание, редактирование, удаление)
- Управление категориями
- Загрузка и управление видео файлами
- Управление синонимами жестов
- Поиск и фильтрация жестов

### База данных
- PostgreSQL с поддержкой JSONB для embeddings
- Автоматическое обновление метаданных синхронизации
- Каскадное удаление связанных данных

## 📁 Структура проекта

```
SignLanguageDictionaryBackend/
├── app/                    # Основное приложение
│   ├── __init__.py        # Инициализация Flask app
│   ├── config.py          # Конфигурация
│   ├── database.py        # Подключение к БД
│   ├── errors.py          # Обработка ошибок
│   ├── models/            # SQLAlchemy модели
│   │   ├── category.py
│   │   ├── sign.py
│   │   ├── sign_video.py
│   │   ├── sign_synonym.py
│   │   ├── sync_metadata.py
│   │   └── admin_user.py
│   ├── routes/            # API endpoints
│   │   ├── sync.py       # Endpoints для мобильного приложения
│   │   └── admin.py      # Административные endpoints
│   └── utils/            # Утилиты
│       ├── auth.py       # JWT авторизация
│       ├── embeddings.py # Генерация embeddings (RuBERT)
│       ├── storage.py    # Хранение видео
│       ├── validators.py # Валидация данных
│       └── sync.py       # Синхронизация метаданных
├── database/              # Схема базы данных
│   ├── init_schema.sql   # SQL схема
│   ├── README.md         # Документация по БД
│   └── QUICK_START.md    # Быстрый старт
├── scripts/              # Вспомогательные скрипты
│   ├── create_admin.py   # Создание администратора
│   ├── create_admin_simple.py
│   └── migrate_from_json.py  # Миграция данных из JSON
├── static/               # Статические файлы
│   ├── css/              # Стили админ-панели
│   ├── js/               # JavaScript админ-панели
│   └── videos/           # Видео файлы (не в git)
├── templates/            # HTML шаблоны
│   ├── login.html
│   ├── dashboard.html
│   ├── signs.html
│   └── categories.html
├── PROMPTS/              # Промпты для разработки
├── requirements.txt      # Python зависимости
├── run.py               # Точка входа приложения
└── README.md            # Этот файл
```

## 🔧 Технологический стек

- **Backend:** Python 3.10+, Flask 3.0+
- **ORM:** SQLAlchemy 2.0+
- **База данных:** PostgreSQL 17+ (совместимо с 14+)
- **Аутентификация:** JWT (PyJWT), bcrypt
- **ML:** Transformers (RuBERT) для генерации embeddings
- **Frontend:** HTML/CSS/JavaScript (vanilla)
- **API документация:** Swagger (Flasgger)

## 📚 API Endpoints

### Для мобильного приложения

- `GET /api/v1/sync/check` - Проверка обновлений
- `GET /api/v1/sync/data` - Получение всех данных

### Административные (требуют авторизации)

- `POST /api/v1/admin/auth/login` - Авторизация
- `GET /api/v1/admin/signs` - Список жестов
- `POST /api/v1/admin/signs` - Создать жест
- `PUT /api/v1/admin/signs/{id}` - Обновить жест
- `DELETE /api/v1/admin/signs/{id}` - Удалить жест
- `GET /api/v1/admin/categories` - Список категорий
- `POST /api/v1/admin/signs/{id}/videos` - Загрузить видео
- И другие...

Полная документация API доступна по адресу: `http://localhost:5001/api-docs` (Swagger UI)

## Веб-административная панель

- **Вход:** `http://localhost:5001/admin/login`
- **Dashboard:** `http://localhost:5001/admin/dashboard`
- **Жесты:** `http://localhost:5001/admin/signs`
- **Категории:** `http://localhost:5001/admin/categories`

## Разработка

### Запуск в режиме разработки

```bash
export FLASK_DEBUG=True
export FLASK_ENV=development
python run.py
```

### Создание администратора

```bash
python scripts/create_admin_simple.py \
    --username admin \
    --password your_password
```

**Важно:** Перед развёртыванием в production:
- Измените `JWT_SECRET_KEY` на случайную строку
- Установите `FLASK_DEBUG=False`
- Настройте HTTPS
- Ограничьте CORS для конкретных доменов

## Развёртывание

### Production

1. Установите зависимости
2. Настройте PostgreSQL на сервере
3. Создайте `.env` с production настройками
4. Примените схему БД
5. Запустите через Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
   ```

## Вклад в проект

Проект разработан для Всероссийского общества глухих (ВОГ).

## Лицензия

Проект для Всероссийского общества глухих (ВОГ).

## 🔗 Полезные ссылки

- [Swagger UI](http://localhost:5001/api-docs) - Интерактивная документация API
- [Административная панель](http://localhost:5001/admin/login) - Веб-интерфейс управления

## Контакты

Для вопросов и предложений создавайте Issues в репозитории.

