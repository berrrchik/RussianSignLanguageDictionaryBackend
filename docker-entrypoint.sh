#!/bin/bash
# Docker entrypoint для приложения
# Автор: Berchik Anastasia Sergeevna

set -e

echo "=============================================="
echo "Sign Language Dictionary Backend"
echo "Автор: Berchik Anastasia Sergeevna"
echo "=============================================="

# Ожидание готовности PostgreSQL
echo "Ожидание готовности базы данных..."
until python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/sign_language_dict'))
    conn.close()
    print('База данных доступна')
except Exception as e:
    print(f'Ожидание: {e}')
    exit(1)
" 2>/dev/null; do
    echo "Ожидание PostgreSQL..."
    sleep 2
done

echo "✓ База данных готова"

# Создание администратора (если не существует)
echo "Проверка/создание администратора..."
python -c "
import os
import sys
sys.path.insert(0, '/app')

from app import create_app
from app.database import db
from app.models.admin_user import AdminUser
import bcrypt

app = create_app()

with app.app_context():
    admin = AdminUser.query.filter_by(username='adminvog').first()
    if not admin:
        password_hash = bcrypt.hashpw('adminvog'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = AdminUser(username='adminvog', password_hash=password_hash)
        db.session.add(admin)
        db.session.commit()
        print('✓ Администратор adminvog создан')
    else:
        print('✓ Администратор adminvog уже существует')
"

echo "=============================================="
echo "Запуск приложения..."
echo "=============================================="

# Запуск основного приложения
exec python run.py
