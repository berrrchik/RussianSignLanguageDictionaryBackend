"""
Integration-тесты для endpoints уроков.
"""
from app.database import db
from app.models.lesson import Lesson


class TestLessonsEndpoints:
    """Тесты для административных endpoints уроков."""
    
    def test_get_lessons_list(self, client, auth_headers, app):
        """Тест получения списка уроков."""
        with app.app_context():
            # Создание тестовых уроков
            lesson1 = Lesson(id='lesson_1', title='Урок 1', description='Описание 1', 
                           video_url='lessons/lesson-1.mp4', order=1)
            lesson2 = Lesson(id='lesson_2', title='Урок 2', description='Описание 2', 
                           video_url='lessons/lesson-2.mp4', order=2)
            db.session.add(lesson1)
            db.session.add(lesson2)
            db.session.commit()
        
        response = client.get('/api/v1/admin/lessons', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['id'] == 'lesson_1'
        assert data['data'][1]['id'] == 'lesson_2'
    
    def test_get_lesson_by_id(self, client, auth_headers, app):
        """Тест получения урока по ID."""
        with app.app_context():
            lesson = Lesson(id='lesson_1', title='Урок 1', description='Описание 1', 
                          video_url='lessons/lesson-1.mp4', order=1)
            db.session.add(lesson)
            db.session.commit()
        
        response = client.get('/api/v1/admin/lessons/lesson_1', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['id'] == 'lesson_1'
        assert data['data']['title'] == 'Урок 1'
    
    def test_create_lesson(self, client, auth_headers, app):
        """Тест создания урока."""
        lesson_data = {
            'title': 'Новый урок',
            'description': 'Описание нового урока',
            'video_url': 'lessons/lesson-12.mp4',
            'order': 12
        }
        
        response = client.post('/api/v1/admin/lessons', 
                             json=lesson_data, 
                             headers=auth_headers)
        assert response.status_code == 201
        
        data = response.get_json()
        assert data['success'] is True
        assert 'id' in data['data']
        assert data['data']['title'] == 'Новый урок'
        
        # Проверка, что урок создан в БД
        with app.app_context():
            lesson = Lesson.query.get(data['data']['id'])
            assert lesson is not None
            assert lesson.title == 'Новый урок'
    
    def test_update_lesson(self, client, auth_headers, app):
        """Тест обновления урока."""
        with app.app_context():
            lesson = Lesson(id='lesson_1', title='Урок 1', description='Описание 1', 
                          video_url='lessons/lesson-1.mp4', order=1)
            db.session.add(lesson)
            db.session.commit()
        
        update_data = {
            'title': 'Обновленный урок',
            'description': 'Новое описание',
            'video_url': 'lessons/lesson-1-updated.mp4',
            'order': 1
        }
        
        response = client.put('/api/v1/admin/lessons/lesson_1', 
                            json=update_data, 
                            headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Обновленный урок'
        
        # Проверка в БД
        with app.app_context():
            lesson = Lesson.query.get('lesson_1')
            assert lesson.title == 'Обновленный урок'
    
    def test_delete_lesson(self, client, auth_headers, app):
        """Тест удаления урока."""
        with app.app_context():
            lesson = Lesson(id='lesson_1', title='Урок 1', description='Описание 1', 
                          video_url='lessons/lesson-1.mp4', order=1)
            db.session.add(lesson)
            db.session.commit()
        
        response = client.delete('/api/v1/admin/lessons/lesson_1', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        
        # Проверка, что урок удален из БД
        with app.app_context():
            lesson = Lesson.query.get('lesson_1')
            assert lesson is None
    
    def test_lessons_require_auth(self, client):
        """Тест, что endpoints требуют авторизацию."""
        response = client.get('/api/v1/admin/lessons')
        assert response.status_code == 401
        
        response = client.post('/api/v1/admin/lessons', json={})
        assert response.status_code == 401


class TestLessonsInSyncEndpoint:
    """Тесты для включения уроков в endpoint синхронизации."""
    
    def test_sync_data_includes_lessons(self, client, app):
        """Тест, что endpoint /api/v1/sync/data/raw включает уроки."""
        with app.app_context():
            lesson = Lesson(id='lesson_1', title='Урок 1', description='Описание 1', 
                          video_url='lessons/lesson-1.mp4', order=1)
            db.session.add(lesson)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data/raw')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'lessons' in data
        assert isinstance(data['lessons'], list)
        assert len(data['lessons']) == 1
        assert data['lessons'][0]['id'] == 'lesson_1'
        assert data['lessons'][0]['title'] == 'Урок 1'
