# Быстрый старт: Создание базы данных

## Если PostgreSQL не установлен

### macOS (через Homebrew)

```bash
brew install postgresql@17
brew services start postgresql@17
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
psql --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
psql --version
```

## Быстрая установка базы данных (3 шага)

### Шаг 1: Создать базу данных

```bash
psql -U postgres
CREATE DATABASE sign_language_dict WITH ENCODING 'UTF8';
\q
```

### Шаг 2: Выполнить скрипт схемы

```bash
cd /path/to/project
psql -U postgres -d sign_language_dict -f database/init_schema.sql
```

**Примечание:** Файл `init_schema.sql` должен находиться в папке `database/` относительно корня проекта. Если вы находитесь в другой директории, используйте абсолютный путь или перейдите в корень проекта.

### Шаг 3: Проверить

```bash
psql -U postgres -d sign_language_dict -c "\dt"
```

Должны увидеть 6 таблиц: `admin_users`, `categories`, `sign_synonyms`, `sign_videos`, `signs`, `sync_metadata`

## Альтернатива: через pgAdmin

1. Откройте **pgAdmin**
2. Создайте базу данных `sign_language_dict` (правой кнопкой на Databases → Create → Database)
3. Откройте Query Tool (правой кнопкой на базу → Query Tool)
4. Откройте файл `database/init_schema.sql` (File → Open)
5. Нажмите Execute (F5)

## Параметры подключения

```
host: localhost
port: 5432
database: sign_language_dict
user: postgres
password: (пароль, установленный при установке PostgreSQL)
```
