"""
Integration-тесты для endpoints синхронизации и моделей.
"""
from datetime import datetime
from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.models.sync_metadata import SyncMetadata
from app.utils.formatters import format_datetime


class TestCategoryToDict:
    """Тесты для Category.to_dict()."""
    
    def test_category_to_dict_includes_sign_count(self, app):
        """Проверка наличия sign_count в Category.to_dict()."""
        with app.app_context():
            category = Category(id="test", name="Test Category", order=1)
            db.session.add(category)
            
            # Добавляем жесты в категорию
            sign1 = Sign(id="s1", word="test1", category_id="test")
            sign2 = Sign(id="s2", word="test2", category_id="test")
            db.session.add(sign1)
            db.session.add(sign2)
            db.session.commit()
            
            result = category.to_dict()
            
            assert 'sign_count' in result
            assert result['sign_count'] == 2
            assert isinstance(result['sign_count'], int)
    
    def test_category_to_dict_sign_count_zero(self, app):
        """Проверка sign_count = 0 для категории без жестов."""
        with app.app_context():
            category = Category(id="empty", name="Empty Category", order=2)
            db.session.add(category)
            db.session.commit()
            
            result = category.to_dict()
            
            assert 'sign_count' in result
            assert result['sign_count'] == 0
    
    def test_category_datetime_format(self, app):
        """Проверка формата дат в Category.to_dict()."""
        with app.app_context():
            category = Category(id="test", name="Test", order=1)
            db.session.add(category)
            db.session.commit()
            
            result = category.to_dict()
            
            if result['created_at']:
                assert result['created_at'].endswith('Z')
                assert 'T' in result['created_at']
            if result['updated_at']:
                assert result['updated_at'].endswith('Z')
                assert 'T' in result['updated_at']


class TestSignVideoToDict:
    """Тесты для SignVideo.to_dict()."""
    
    def test_sign_video_always_has_context_description(self, app):
        """Проверка наличия context_description в SignVideo.to_dict()."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            # Видео с пустым context_description
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="",
                order=0
            )
            db.session.add(video)
            db.session.commit()
            
            result = video.to_dict()
            
            assert 'context_description' in result
            assert result['context_description'] != ""
            assert result['context_description'] is not None
            assert result['context_description'] == "Основное видео"
    
    def test_sign_video_context_description_default_for_order_zero(self, app):
        """Проверка значения по умолчанию для order=0."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description=None,
                order=0
            )
            db.session.add(video)
            db.session.commit()
            
            result = video.to_dict()
            assert result['context_description'] == "Основное видео"
    
    def test_sign_video_context_description_default_for_order_greater_zero(self, app):
        """Проверка значения по умолчанию для order > 0."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="",
                order=2
            )
            db.session.add(video)
            db.session.commit()
            
            result = video.to_dict()
            assert result['context_description'] == "Видео 3"
    
    def test_sign_video_preserves_existing_context_description(self, app):
        """Проверка сохранения существующего context_description."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="Кастомное описание",
                order=0
            )
            db.session.add(video)
            db.session.commit()
            
            result = video.to_dict()
            assert result['context_description'] == "Кастомное описание"
    
    def test_sign_video_datetime_format(self, app):
        """Проверка формата дат в SignVideo.to_dict()."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="Test",
                order=0
            )
            db.session.add(video)
            db.session.commit()
            
            result = video.to_dict()
            
            if result['created_at']:
                assert result['created_at'].endswith('Z')
                assert 'T' in result['created_at']
            if result['updated_at']:
                assert result['updated_at'].endswith('Z')
                assert 'T' in result['updated_at']


class TestSignToDict:
    """Тесты для Sign.to_dict() и Sign.to_dict_with_relations()."""
    
    def test_sign_datetime_format(self, app):
        """Проверка формата дат в Sign.to_dict()."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            db.session.commit()
            
            result = sign.to_dict()
            
            if result['created_at']:
                assert result['created_at'].endswith('Z')
                assert 'T' in result['created_at']
            if result['updated_at']:
                assert result['updated_at'].endswith('Z')
                assert 'T' in result['updated_at']
    
    def test_sign_to_dict_with_relations_datetime_format(self, app):
        """Проверка формата дат в Sign.to_dict_with_relations()."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            db.session.commit()
            
            result = sign.to_dict_with_relations()
            
            if result['created_at']:
                assert result['created_at'].endswith('Z')
                assert 'T' in result['created_at']
            if result['updated_at']:
                assert result['updated_at'].endswith('Z')
                assert 'T' in result['updated_at']


class TestFormatDatetime:
    """Тесты для функции format_datetime()."""
    
    def test_format_datetime_has_z_suffix(self):
        """Проверка наличия 'Z' суффикса в формате даты."""
        dt = datetime(2025, 12, 4, 12, 7, 58, 765345)
        formatted = format_datetime(dt)
        
        assert formatted.endswith('Z')
        assert 'T' in formatted
        assert formatted == "2025-12-04T12:07:58.765345Z"
    
    def test_format_datetime_none_returns_none(self):
        """Проверка возврата None для None значения."""
        assert format_datetime(None) is None
    
    def test_format_datetime_iso_format(self):
        """Проверка корректности ISO формата."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        formatted = format_datetime(dt)
        
        assert formatted.startswith("2025-01-15T10:30:00")
        assert formatted.endswith('Z')


class TestSyncEndpoints:
    """Тесты для endpoints синхронизации."""
    
    def test_sync_check_returns_correct_date_format(self, app, client):
        """Проверка формата даты в ответе /sync/check."""
        with app.app_context():
            metadata = SyncMetadata(last_updated=datetime(2025, 12, 4, 12, 7, 58))
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/check')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'last_updated' in data['data']
        
        last_updated = data['data']['last_updated']
        assert last_updated.endswith('Z')
        assert 'T' in last_updated
    
    def test_sync_data_returns_all_required_fields(self, app, client):
        """Проверка наличия всех обязательных полей в ответе /sync/data."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            
            sign = Sign(id="s1", word="test", category_id="cat1")
            db.session.add(sign)
            
            video = SignVideo(
                id=1,
                sign_id="s1",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="Test video",
                order=0
            )
            db.session.add(video)
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        
        response_data = data['data']
        assert 'categories' in response_data
        assert 'signs' in response_data
        assert 'last_updated' in response_data
        
        # Проверка категории
        category = response_data['categories'][0]
        assert 'sign_count' in category
        assert isinstance(category['sign_count'], int)
        
        # Проверка жеста
        sign = response_data['signs'][0]
        assert 'videos' in sign
        assert len(sign['videos']) > 0
        
        # Проверка видео
        video = sign['videos'][0]
        assert 'context_description' in video
        assert video['context_description'] is not None
        assert video['context_description'] != ""
        
        # Проверка формата даты
        assert response_data['last_updated'].endswith('Z')
    
    def test_sync_data_validates_signs_without_videos(self, app, client):
        """Проверка валидации жестов без видео."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            
            # Жест без видео
            sign_without_video = Sign(id="s1", word="test1", category_id="cat1")
            db.session.add(sign_without_video)
            
            # Жест с видео
            sign_with_video = Sign(id="s2", word="test2", category_id="cat1")
            db.session.add(sign_with_video)
            
            video = SignVideo(
                id=1,
                sign_id="s2",
                url="http://test.com/video.mp4",
                file_path="/path/to/video.mp4",
                context_description="Test",
                order=0
            )
            db.session.add(video)
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data')
        assert response.status_code == 200
        
        data = response.get_json()
        # Жест без видео всё равно должен быть в ответе (обратная совместимость)
        signs = data['data']['signs']
        assert len(signs) == 2
