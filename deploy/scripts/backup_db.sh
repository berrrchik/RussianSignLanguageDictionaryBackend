#!/bin/bash
# Скрипт для резервного копирования базы данных

# Настройки (заполните своими значениями)
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sign_language_dict"
DB_HOST="c-xxxxx.rw.mdb.yandexcloud.net"  # Замените на ваш FQDN
DB_PORT="6432"
DB_USER="postgres"
DB_PASSWORD=""  # Будет запрошен или используйте PGPASSWORD

# Создаём директорию для бэкапов
mkdir -p "$BACKUP_DIR"

# Функция для логирования
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$BACKUP_DIR/backup.log"
}

log_message "🔄 Starting database backup..."

# Используем PGPASSWORD если установлен, иначе запрашиваем
if [ -z "$DB_PASSWORD" ]; then
    if [ -z "$PGPASSWORD" ]; then
        echo "Please set DB_PASSWORD or PGPASSWORD environment variable"
        exit 1
    fi
    export PGPASSWORD
else
    export PGPASSWORD="$DB_PASSWORD"
fi

# Создаём бэкап
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.dump"
if PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F c -f "$BACKUP_FILE" 2>&1 | tee -a "$BACKUP_DIR/backup.log"; then
    log_message "✅ Backup created successfully: $BACKUP_FILE"
    
    # Сжимаем бэкап (опционально)
    # gzip "$BACKUP_FILE"
    # log_message "✅ Backup compressed: ${BACKUP_FILE}.gz"
else
    log_message "❌ Backup failed!"
    exit 1
fi

# Удаляем старые бэкапы (старше 7 дней)
log_message "🧹 Cleaning old backups (older than 7 days)..."
find "$BACKUP_DIR" -name "backup_*.dump" -mtime +7 -delete
find "$BACKUP_DIR" -name "backup_*.dump.gz" -mtime +7 -delete

log_message "✅ Backup process completed"
