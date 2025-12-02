"""
Административные endpoints для управления контентом.
"""
import os
from pathlib import Path
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, render_template
import bcrypt

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.models.sign_synonym import SignSynonym
from app.models.admin_user import AdminUser
from app.utils.auth import require_auth, generate_token
from app.utils.sync import update_sync_metadata
from app.utils.validators import (
    validate_sign_data,
    validate_category_data,
    validate_video_data,
    validate_embeddings
)
from app.utils.embeddings import get_embedding_generator

bp = Blueprint('admin', __name__)


# ==================== Авторизация ====================

@bp.route('/auth/login', methods=['POST'])
def login():
    """
    Авторизация администратора
    ---
    tags:
      - Авторизация
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: admin
            password:
              type: string
              example: password
    responses:
      200:
        description: Успешная авторизация
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                token:
                  type: string
                  example: "eyJ0eXAiOiJKV1QiLCJhbGc..."
                expires_in:
                  type: integer
                  example: 3600
      401:
        description: Неверные учетные данные
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_CREDENTIALS',
                    'message': 'Требуются username и password'
                }
            }), 400
        
        user = AdminUser.query.filter_by(username=username).first()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            # Обновление last_login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Генерация токена
            token = generate_token(
                user.id,
                current_app.config['JWT_SECRET_KEY'],
                current_app.config['JWT_EXPIRATION_DELTA']
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'token': token,
                    'expires_in': current_app.config['JWT_EXPIRATION_DELTA']
                }
            })
        
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': 'Неверный username или password'
            }
        }), 401
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка авторизации: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка авторизации'
            }
        }), 500


# ==================== CRUD для жестов ====================

@bp.route('/signs', methods=['GET'])
@require_auth
def list_signs():
    """
    Получение списка жестов с пагинацией
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Номер страницы
      - name: per_page
        in: query
        type: integer
        default: 50
        description: Количество на странице
      - name: category_id
        in: query
        type: string
        required: false
        description: Фильтр по категории
      - name: search
        in: query
        type: string
        required: false
        description: Поиск по слову или ID
    responses:
      200:
        description: Список жестов
      401:
        description: Неавторизован
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        category_id = request.args.get('category_id')
        search = request.args.get('search', '').strip()
        
        query = Sign.query
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if search:
            # Поиск по слову или ID (без учета регистра)
            search_pattern = f'%{search}%'
            query = query.filter(
                (Sign.word.ilike(search_pattern)) |
                (Sign.id.ilike(search_pattern))
            )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': {
                'signs': [sign.to_dict() for sign in pagination.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка жестов: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка получения списка жестов'
            }
        }), 500


@bp.route('/signs/<sign_id>', methods=['GET'])
@require_auth
def get_sign(sign_id):
    """
    Получение жеста по ID
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
        description: ID жеста
    responses:
      200:
        description: Данные жеста
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        return jsonify({
            'success': True,
            'data': sign.to_dict_with_relations()
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения жеста: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Жест не найден'
            }
        }), 404


@bp.route('/signs', methods=['POST'])
@require_auth
def create_sign():
    """
    Создание нового жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - id
            - word
            - category_id
          properties:
            id:
              type: string
              example: "sign_001"
            word:
              type: string
              example: "привет"
            description:
              type: string
              example: "Приветствие"
            category_id:
              type: string
              example: "greetings"
    responses:
      201:
        description: Жест создан
      400:
        description: Ошибка валидации
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        # Валидация
        errors = validate_sign_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': '; '.join(errors)
                }
            }), 400
        
        # Проверка существования категории
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'CATEGORY_NOT_FOUND',
                    'message': 'Категория не найдена'
                }
            }), 400
        
        # Проверка уникальности ID
        if Sign.query.get(data.get('id')):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DUPLICATE_ID',
                    'message': 'Жест с таким ID уже существует'
                }
            }), 400
        
        # Генерация embeddings
        embeddings = None
        generator = get_embedding_generator()
        if generator:
            try:
                embeddings = generator.generate(
                    data['word'],
                    data.get('description')
                )
                if not validate_embeddings(embeddings):
                    current_app.logger.warning(f"Невалидные embeddings для жеста {data.get('id')}")
                    embeddings = None
            except Exception as e:
                current_app.logger.error(f"Ошибка генерации embeddings: {e}")
                embeddings = None
        else:
            current_app.logger.warning("Генерация embeddings пропущена: модель не загружена")
        
        # Создание жеста
        sign = Sign(
            id=data['id'],
            word=data['word'],
            description=data.get('description'),
            category_id=data['category_id'],
            embeddings=embeddings
        )
        db.session.add(sign)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': sign.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка создания жеста: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка создания жеста'
            }
        }), 500


@bp.route('/signs/<sign_id>', methods=['PUT'])
@require_auth
def update_sign(sign_id):
    """
    Обновление жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            word:
              type: string
            description:
              type: string
            category_id:
              type: string
    responses:
      200:
        description: Жест обновлён
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        # Валидация
        errors = validate_sign_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': '; '.join(errors)
                }
            }), 400
        
        # Обновление полей
        if 'word' in data:
            sign.word = data['word']
        if 'description' in data:
            sign.description = data.get('description')
        if 'category_id' in data:
            category = Category.query.get(data['category_id'])
            if not category:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'CATEGORY_NOT_FOUND',
                        'message': 'Категория не найдена'
                    }
                }), 400
            sign.category_id = data['category_id']
        
        # Перегенерация embeddings если изменился текст
        if 'word' in data or 'description' in data:
            generator = get_embedding_generator()
            if generator:
                try:
                    sign.embeddings = generator.generate(sign.word, sign.description)
                    if not validate_embeddings(sign.embeddings):
                        current_app.logger.warning(f"Невалидные embeddings для жеста {sign_id}")
                        sign.embeddings = None
                except Exception as e:
                    current_app.logger.error(f"Ошибка перегенерации embeddings: {e}")
                    sign.embeddings = None
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': sign.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления жеста: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка обновления жеста'
            }
        }), 500


@bp.route('/signs/<sign_id>', methods=['DELETE'])
@require_auth
def delete_sign(sign_id):
    """
    Удаление жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Жест удалён
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        db.session.delete(sign)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Жест удалён'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления жеста: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка удаления жеста'
            }
        }), 500


@bp.route('/signs/<sign_id>/regenerate-embeddings', methods=['POST'])
@require_auth
def regenerate_embeddings(sign_id):
    """
    Перегенерация embeddings для жеста
    ---
    tags:
      - Жесты
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Embeddings перегенерированы
      404:
        description: Жест не найден
      503:
        description: Модель недоступна
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        
        generator = get_embedding_generator()
        if not generator:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MODEL_NOT_AVAILABLE',
                    'message': 'Модель для генерации embeddings недоступна'
                }
            }), 503
        
        try:
            embeddings = generator.generate(sign.word, sign.description)
            if validate_embeddings(embeddings):
                sign.embeddings = embeddings
                db.session.commit()
                update_sync_metadata()
                return jsonify({
                    'success': True,
                    'data': sign.to_dict()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_EMBEDDINGS',
                        'message': 'Сгенерированные embeddings невалидны'
                    }
                }), 500
        except Exception as e:
            current_app.logger.error(f"Ошибка перегенерации embeddings: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'GENERATION_FAILED',
                    'message': 'Ошибка генерации embeddings'
                }
            }), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка перегенерации embeddings: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка перегенерации embeddings'
            }
        }), 500


# ==================== CRUD для видео ====================

@bp.route('/signs/<sign_id>/videos', methods=['GET'])
@require_auth
def list_videos(sign_id):
    """
    Получение списка видео для жеста
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Список видео
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        videos = SignVideo.query.filter_by(sign_id=sign_id).order_by(SignVideo.order).all()
        return jsonify({
            'success': True,
            'data': [video.to_dict() for video in videos]
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка видео: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка получения списка видео'
            }
        }), 500


@bp.route('/signs/<sign_id>/videos', methods=['POST'])
@require_auth
def upload_video(sign_id):
    """
    Загрузка видео для жеста
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: file
        in: formData
        type: file
        required: true
        description: MP4 видео файл (макс. 50MB)
      - name: context_description
        in: formData
        type: string
        required: true
        description: Описание контекста использования
      - name: order
        in: formData
        type: integer
        required: false
        default: 0
        description: Порядок отображения
    responses:
      201:
        description: Видео загружено
      400:
        description: Ошибка валидации
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': 'Файл не загружен'
                }
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': 'Файл не выбран'
                }
            }), 400
        
        # Валидация
        form_data = {
            'context_description': request.form.get('context_description', ''),
            'order': request.form.get('order', 0)
        }
        errors = validate_video_data(form_data, file)
        if errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': '; '.join(errors)
                }
            }), 400
        
        # Проверка формата
        if not file.filename.lower().endswith('.mp4'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FORMAT',
                    'message': 'Поддерживается только формат MP4'
                }
            }), 400
        
        # Проверка размера
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > current_app.config['VIDEO_MAX_SIZE']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FILE_TOO_LARGE',
                    'message': f'Размер файла не должен превышать {current_app.config["VIDEO_MAX_SIZE"] // (1024*1024)}MB'
                }
            }), 400
        
        # Сохранение файла через абстракцию хранилища
        from app.utils.storage import get_video_storage
        
        storage = get_video_storage()
        file_path, url = storage.upload(file, sign_id, file.filename)
        
        # Создание записи в БД
        video = SignVideo(
            sign_id=sign_id,
            file_path=file_path,
            url=url,
            context_description=request.form['context_description'],
            order=int(request.form.get('order', 0))
        )
        db.session.add(video)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': video.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка загрузки видео: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка загрузки видео'
            }
        }), 500


@bp.route('/videos/<int:video_id>', methods=['PUT'])
@require_auth
def update_video(video_id):
    """
    Обновление видео
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: video_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            context_description:
              type: string
            order:
              type: integer
    responses:
      200:
        description: Видео обновлено
      404:
        description: Видео не найдено
    """
    try:
        video = SignVideo.query.get_or_404(video_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        if 'context_description' in data:
            video.context_description = data['context_description']
        if 'order' in data:
            video.order = int(data['order'])
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': video.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления видео: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка обновления видео'
            }
        }), 500


@bp.route('/videos/<int:video_id>', methods=['DELETE'])
@require_auth
def delete_video(video_id):
    """
    Удаление видео
    ---
    tags:
      - Видео
    security:
      - Bearer: []
    parameters:
      - name: video_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Видео удалено
      404:
        description: Видео не найдено
    """
    try:
        video = SignVideo.query.get_or_404(video_id)
        
        # Удаление файла через абстракцию хранилища
        from app.utils.storage import get_video_storage
        
        storage = get_video_storage()
        if not storage.delete(video.file_path):
            current_app.logger.warning(f"Не удалось удалить файл {video.file_path}")
        
        db.session.delete(video)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Видео удалено'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления видео: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка удаления видео'
            }
        }), 500


# ==================== Управление синонимами ====================

@bp.route('/signs/<sign_id>/synonyms', methods=['GET'])
@require_auth
def list_synonyms(sign_id):
    """
    Получение списка синонимов для жеста
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Список синонимов
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        
        # Получение всех связей синонимов
        synonyms_query = SignSynonym.query.filter(
            (SignSynonym.sign_id_1 == sign_id) | (SignSynonym.sign_id_2 == sign_id)
        ).all()
        
        synonyms = []
        for synonym in synonyms_query:
            other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == sign_id else synonym.sign_id_1
            other_sign = Sign.query.get(other_sign_id)
            if other_sign:
                synonyms.append({
                    'id': other_sign.id,
                    'word': other_sign.word
                })
        
        return jsonify({
            'success': True,
            'data': synonyms
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка синонимов: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка получения списка синонимов'
            }
        }), 500


@bp.route('/signs/<sign_id>/synonyms', methods=['POST'])
@require_auth
def add_synonym(sign_id):
    """
    Добавление синонима для жеста
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - synonym_sign_id
          properties:
            synonym_sign_id:
              type: string
              example: "sign_002"
    responses:
      201:
        description: Синоним добавлен
      400:
        description: Ошибка валидации
      404:
        description: Жест не найден
    """
    try:
        sign = Sign.query.get_or_404(sign_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        synonym_id = data.get('synonym_sign_id')
        if not synonym_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELD',
                    'message': 'Требуется поле synonym_sign_id'
                }
            }), 400
        
        # Проверка существования жеста-синонима
        synonym_sign = Sign.query.get(synonym_id)
        if not synonym_sign:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SIGN_NOT_FOUND',
                    'message': 'Жест-синоним не найден'
                }
            }), 404
        
        if sign_id == synonym_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_SYNONYM',
                    'message': 'Жест не может быть синонимом самому себе'
                }
            }), 400
        
        # Проверка существования связи
        existing = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == sign_id) & (SignSynonym.sign_id_2 == synonym_id)) |
            ((SignSynonym.sign_id_1 == synonym_id) & (SignSynonym.sign_id_2 == sign_id))
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SYNONYM_EXISTS',
                    'message': 'Связь синонимов уже существует'
                }
            }), 400
        
        # Создание двусторонней связи
        synonym1 = SignSynonym(sign_id_1=sign_id, sign_id_2=synonym_id)
        synonym2 = SignSynonym(sign_id_1=synonym_id, sign_id_2=sign_id)
        
        db.session.add(synonym1)
        db.session.add(synonym2)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Синоним добавлен'
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка добавления синонима: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка добавления синонима'
            }
        }), 500


@bp.route('/signs/<sign_id>/synonyms/<synonym_id>', methods=['DELETE'])
@require_auth
def delete_synonym(sign_id, synonym_id):
    """
    Удаление связи синонимов
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: sign_id
        in: path
        type: string
        required: true
      - name: synonym_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Связь синонимов удалена
      404:
        description: Связь не найдена
    """
    try:
        # Удаление обеих связей (двусторонних)
        synonyms = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == sign_id) & (SignSynonym.sign_id_2 == synonym_id)) |
            ((SignSynonym.sign_id_1 == synonym_id) & (SignSynonym.sign_id_2 == sign_id))
        ).all()
        
        if not synonyms:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SYNONYM_NOT_FOUND',
                    'message': 'Связь синонимов не найдена'
                }
            }), 404
        
        for synonym in synonyms:
            db.session.delete(synonym)
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Связь синонимов удалена'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления синонима: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка удаления синонима'
            }
        }), 500


@bp.route('/synonyms/<int:synonym_id>', methods=['DELETE'])
@require_auth
def delete_synonym_by_id(synonym_id):
    """
    Удаление связи синонимов по ID связи
    ---
    tags:
      - Синонимы
    security:
      - Bearer: []
    parameters:
      - name: synonym_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Связь синонимов удалена
      404:
        description: Связь не найдена
    """
    try:
        synonym = SignSynonym.query.get_or_404(synonym_id)
        
        # Удаление обеих связей (двусторонних)
        synonyms = SignSynonym.query.filter(
            ((SignSynonym.sign_id_1 == synonym.sign_id_1) & (SignSynonym.sign_id_2 == synonym.sign_id_2)) |
            ((SignSynonym.sign_id_1 == synonym.sign_id_2) & (SignSynonym.sign_id_2 == synonym.sign_id_1))
        ).all()
        
        for syn in synonyms:
            db.session.delete(syn)
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Связь синонимов удалена'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления синонима: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка удаления синонима'
            }
        }), 500


# ==================== CRUD для категорий ====================

@bp.route('/categories', methods=['GET'])
@require_auth
def list_categories():
    """
    Получение списка категорий
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    responses:
      200:
        description: Список категорий
    """
    try:
        categories = Category.query.order_by(Category.order).all()
        return jsonify({
            'success': True,
            'data': [cat.to_dict() for cat in categories]
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка категорий: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка получения списка категорий'
            }
        }), 500


@bp.route('/categories/<category_id>', methods=['GET'])
@require_auth
def get_category(category_id):
    """
    Получение категории по ID
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Данные категории
      404:
        description: Категория не найдена
    """
    try:
        category = Category.query.get_or_404(category_id)
        return jsonify({
            'success': True,
            'data': category.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения категории: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Категория не найдена'
            }
        }), 404


@bp.route('/categories', methods=['POST'])
@require_auth
def create_category():
    """
    Создание новой категории
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - id
            - name
          properties:
            id:
              type: string
              example: "alphabet"
            name:
              type: string
              example: "Алфавит"
            order:
              type: integer
              example: 1
    responses:
      201:
        description: Категория создана
      400:
        description: Ошибка валидации
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        # Валидация
        errors = validate_category_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': '; '.join(errors)
                }
            }), 400
        
        # Проверка уникальности ID
        if Category.query.get(data.get('id')):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DUPLICATE_ID',
                    'message': 'Категория с таким ID уже существует'
                }
            }), 400
        
        category = Category(
            id=data['id'],
            name=data['name'],
            order=data.get('order', 0)
        )
        db.session.add(category)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': category.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка создания категории: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка создания категории'
            }
        }), 500


@bp.route('/categories/<category_id>', methods=['PUT'])
@require_auth
def update_category(category_id):
    """
    Обновление категории
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            order:
              type: integer
    responses:
      200:
        description: Категория обновлена
      404:
        description: Категория не найдена
    """
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Требуется JSON тело запроса'
                }
            }), 400
        
        # Валидация
        errors = validate_category_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': '; '.join(errors)
                }
            }), 400
        
        if 'name' in data:
            category.name = data['name']
        if 'order' in data:
            category.order = data['order']
        
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'data': category.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка обновления категории: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка обновления категории'
            }
        }), 500


@bp.route('/categories/<category_id>', methods=['DELETE'])
@require_auth
def delete_category(category_id):
    """
    Удаление категории
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Категория удалена
      400:
        description: В категории есть жесты
      404:
        description: Категория не найдена
    """
    try:
        category = Category.query.get_or_404(category_id)
        
        # Проверка наличия жестов в категории
        signs_count = Sign.query.filter_by(category_id=category_id).count()
        if signs_count > 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'CATEGORY_HAS_SIGNS',
                    'message': f'Невозможно удалить категорию: в ней содержится {signs_count} жестов'
                }
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        # Обновление метаданных синхронизации
        update_sync_metadata()
        
        return jsonify({
            'success': True,
            'message': 'Категория удалена'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка удаления категории: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка удаления категории'
            }
        }), 500


@bp.route('/categories/<category_id>/signs', methods=['GET'])
@require_auth
def get_category_signs(category_id):
    """
    Получение жестов категории
    ---
    tags:
      - Категории
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Список жестов категории
      404:
        description: Категория не найдена
    """
    try:
        category = Category.query.get_or_404(category_id)
        signs = Sign.query.filter_by(category_id=category_id).all()
        return jsonify({
            'success': True,
            'data': [sign.to_dict() for sign in signs]
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка получения жестов категории: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Ошибка получения жестов категории'
            }
        }), 500


# ==================== HTML страницы административной панели ====================

# Отдельный blueprint для HTML страниц
admin_pages_bp = Blueprint('admin_pages', __name__)


@admin_pages_bp.route('/login', methods=['GET'])
def login_page():
    """Страница входа в административную панель."""
    return render_template('login.html')


@admin_pages_bp.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Главная страница административной панели."""
    return render_template('dashboard.html')


@admin_pages_bp.route('/signs', methods=['GET'])
def signs_page():
    """Страница управления жестами."""
    return render_template('signs.html')


@admin_pages_bp.route('/categories', methods=['GET'])
def categories_page():
    """Страница управления категориями."""
    return render_template('categories.html')

