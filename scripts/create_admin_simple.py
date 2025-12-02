#!/usr/bin/env python3
"""
Простой скрипт для создания администратора через psycopg2 напрямую.
Не требует Flask, только bcrypt и psycopg2.
"""
import argparse
import sys
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ Ошибка: psycopg2 не установлен")
    print("Установите: pip install psycopg2-binary bcrypt python-dotenv")
    sys.exit(1)


def create_admin_user(username: str, password: str, database_url: str = None):
    """
    Создаёт администратора в базе данных.
    """
    if not database_url:
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/sign_language_dict'
        )
    
    try:
        # Подключение к БД
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Проверка существования пользователя
        cur.execute("SELECT id FROM admin_users WHERE username = %s", (username,))
        if cur.fetchone():
            print(f"❌ Пользователь '{username}' уже существует!")
            cur.close()
            conn.close()
            return False
        
        # Хеширование пароля
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Создание пользователя
        cur.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Администратор '{username}' успешно создан!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Создание администратора')
    parser.add_argument('--username', required=True, help='Имя пользователя')
    parser.add_argument('--password', required=True, help='Пароль')
    parser.add_argument('--database-url', help='URL базы данных (опционально)')
    
    args = parser.parse_args()
    
    if not create_admin_user(args.username, args.password, args.database_url):
        sys.exit(1)


if __name__ == '__main__':
    main()

