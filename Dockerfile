# Dockerfile для приложения словаря жестового языка
# Контейнер: sign-language-backend
# Автор: Berchik Anastasia Sergeevna

FROM python:3.11-slim

# Метаданные
LABEL maintainer="Berchik Anastasia Sergeevna"
LABEL description="Sign Language Dictionary Backend"
LABEL version="1.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для логов
RUN mkdir -p /var/log/app

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /var/log/app
USER appuser

# Переменные окружения
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV LOG_FILE=/var/log/app/application.log

# Порт приложения
EXPOSE 5001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api-docs || exit 1

# Копирование и установка прав на entrypoint
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Запуск через entrypoint (создаёт админа и запускает приложение)
ENTRYPOINT ["/app/docker-entrypoint.sh"]
