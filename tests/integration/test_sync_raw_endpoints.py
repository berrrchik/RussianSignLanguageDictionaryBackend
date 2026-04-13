"""
Integration-тесты для /raw endpoints синхронизации.

Тестируют упрощенные эндпоинты с Unix timestamp датами и без обертки {success, data}.
"""
from datetime import datetime, timezone
from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.models.sync_metadata import SyncMetadata
from app.utils.serializers import serialize_datetime, deserialize_datetime


class TestSerializeDatetime:
    """Тесты для функций serialize_datetime и deserialize_datetime."""
    
    def test_serialize_datetime_returns_int(self):
        """Проверка что serialize_datetime возвращает целое число."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = serialize_datetime(dt)
        
        assert isinstance(result, int)
        assert result == 1736937000
    
    def test_serialize_datetime_none_returns_none(self):
        """Проверка что serialize_datetime возвращает None для None."""
        assert serialize_datetime(None) is None
    
    def test_serialize_datetime_naive_assumes_utc(self):
        """Проверка что naive datetime обрабатывается как UTC."""
        dt_naive = datetime(2025, 1, 15, 10, 30, 0)
        dt_utc = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        assert serialize_datetime(dt_naive) == serialize_datetime(dt_utc)
    
    def test_deserialize_datetime_returns_datetime(self):
        """Проверка что deserialize_datetime возвращает datetime."""
        timestamp = 1736935800
        result = deserialize_datetime(timestamp)
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
    
    def test_deserialize_datetime_none_returns_none(self):
        """Проверка что deserialize_datetime возвращает None для None."""
        assert deserialize_datetime(None) is None
    
    def test_roundtrip_serialization(self):
        """Проверка что serialize -> deserialize дает исходное значение."""
        original = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        serialized = serialize_datetime(original)
        deserialized = deserialize_datetime(serialized)
        
        # Микросекунды теряются при сериализации в секунды
        assert deserialized.year == original.year
        assert deserialized.month == original.month
        assert deserialized.day == original.day
        assert deserialized.hour == original.hour
        assert deserialized.minute == original.minute
        assert deserialized.second == original.second


class TestCheckUpdatesRaw:
    """Тесты для GET /api/v1/sync/check/raw."""
    
    def test_check_updates_raw_returns_correct_structure(self, app, client):
        """Проверка структуры ответа без обертки."""
        with app.app_context():
            metadata = SyncMetadata(last_updated=datetime(2025, 12, 4, 12, 7, 58))
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/check/raw')
        assert response.status_code == 200
        
        data = response.get_json()
        
        # Проверка отсутствия обертки
        assert 'success' not in data
        assert 'data' not in data
        
        # Проверка наличия полей
        assert 'last_updated' in data
        assert 'has_updates' in data
    
    def test_check_updates_raw_timestamp_is_integer(self, app, client):
        """Проверка что last_updated - целое число (Unix timestamp)."""
        with app.app_context():
            metadata = SyncMetadata(last_updated=datetime(2025, 12, 4, 12, 7, 58))
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/check/raw')
        data = response.get_json()
        
        assert isinstance(data['last_updated'], int)
        assert isinstance(data['has_updates'], bool)
    
    def test_check_updates_raw_has_updates_true_without_param(self, app, client):
        """Проверка что has_updates=true без параметра last_updated."""
        with app.app_context():
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/check/raw')
        data = response.get_json()
        
        assert data['has_updates'] is True
    
    def test_check_updates_raw_has_updates_false_when_no_changes(self, app, client):
        """Проверка что has_updates=false когда нет изменений."""
        with app.app_context():
            server_time = datetime(2025, 1, 15, 10, 0, 0)
            metadata = SyncMetadata(last_updated=server_time)
            db.session.add(metadata)
            db.session.commit()
        
        # Клиент обновлялся позже сервера
        future_timestamp = serialize_datetime(datetime(2025, 1, 15, 12, 0, 0))
        response = client.get(f'/api/v1/sync/check/raw?last_updated={future_timestamp}')
        data = response.get_json()
        
        assert data['has_updates'] is False
    
    def test_check_updates_raw_has_updates_true_when_changes_exist(self, app, client):
        """Проверка что has_updates=true когда есть изменения."""
        with app.app_context():
            server_time = datetime(2025, 1, 15, 12, 0, 0)
            metadata = SyncMetadata(last_updated=server_time)
            db.session.add(metadata)
            db.session.commit()
        
        # Клиент обновлялся раньше сервера
        past_timestamp = serialize_datetime(datetime(2025, 1, 15, 10, 0, 0))
        response = client.get(f'/api/v1/sync/check/raw?last_updated={past_timestamp}')
        data = response.get_json()
        
        assert data['has_updates'] is True
    
    def test_check_updates_raw_invalid_timestamp_returns_400(self, app, client):
        """Проверка что невалидный timestamp возвращает 400."""
        with app.app_context():
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/check/raw?last_updated=invalid')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'ValidationError'
        assert 'message' in data
    
    def test_check_updates_raw_creates_metadata_if_not_exists(self, app, client):
        """Проверка что metadata создается если не существует."""
        response = client.get('/api/v1/sync/check/raw')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'last_updated' in data


class TestGetSyncDataRaw:
    """Тесты для GET /api/v1/sync/data/raw."""
    
    def test_sync_data_raw_returns_correct_structure(self, app, client):
        """Проверка структуры ответа без обертки."""
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
        
        response = client.get('/api/v1/sync/data/raw')
        assert response.status_code == 200
        
        data = response.get_json()
        
        # Проверка отсутствия обертки
        assert 'success' not in data
        assert 'data' not in data
        
        # Проверка структуры
        assert 'categories' in data
        assert 'signs' in data
        assert 'last_updated' in data
    
    def test_sync_data_raw_timestamps_are_integers(self, app, client):
        """Проверка что все timestamps - целые числа."""
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
        
        response = client.get('/api/v1/sync/data/raw')
        data = response.get_json()
        
        # Проверка корневого last_updated
        assert isinstance(data['last_updated'], int)
        
        # Проверка категорий
        category = data['categories'][0]
        assert isinstance(category['created_at'], int)
        assert isinstance(category['updated_at'], int)
        
        # Проверка жестов
        sign = data['signs'][0]
        assert isinstance(sign['created_at'], int)
        assert isinstance(sign['updated_at'], int)
        
        # Проверка видео
        video = sign['videos'][0]
        assert isinstance(video['created_at'], int)
        assert isinstance(video['updated_at'], int)
    
    def test_sync_data_raw_category_has_sign_count(self, app, client):
        """Проверка наличия sign_count в категориях."""
        with app.app_context():
            category = Category(id="cat1", name="Test Category", order=1)
            db.session.add(category)
            
            sign1 = Sign(id="s1", word="test1", category_id="cat1")
            sign2 = Sign(id="s2", word="test2", category_id="cat1")
            db.session.add(sign1)
            db.session.add(sign2)
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data/raw')
        data = response.get_json()
        
        category = data['categories'][0]
        assert 'sign_count' in category
        assert category['sign_count'] == 2
        assert isinstance(category['sign_count'], int)
    
    def test_sync_data_raw_video_has_context_description(self, app, client):
        """Проверка что видео всегда имеет context_description."""
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
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data/raw')
        data = response.get_json()
        
        video = data['signs'][0]['videos'][0]
        assert 'context_description' in video
        assert video['context_description'] != ""
        assert video['context_description'] == "Основное видео"
    
    def test_sync_data_raw_sign_has_synonyms_field(self, app, client):
        """Проверка наличия поля synonyms в жестах."""
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
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data/raw')
        data = response.get_json()
        
        sign = data['signs'][0]
        assert 'synonyms' in sign
        assert isinstance(sign['synonyms'], list)
    
    def test_sync_data_raw_snake_case_keys(self, app, client):
        """Проверка что все ключи в snake_case."""
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
            
            metadata = SyncMetadata(last_updated=datetime.utcnow())
            db.session.add(metadata)
            db.session.commit()
        
        response = client.get('/api/v1/sync/data/raw')
        data = response.get_json()
        
        # Проверка snake_case ключей
        assert 'last_updated' in data
        
        category = data['categories'][0]
        assert 'sign_count' in category
        assert 'created_at' in category
        assert 'updated_at' in category
        
        sign = data['signs'][0]
        assert 'category_id' in sign
        assert 'created_at' in sign
        assert 'updated_at' in sign
        
        video = sign['videos'][0]
        assert 'context_description' in video
        assert 'created_at' in video
        assert 'updated_at' in video


class TestRemovedSyncEndpoints:
    """Тесты, что удаленные legacy endpoints больше не доступны."""

    def test_removed_embeddings_endpoint_returns_404(self, client):
        response = client.get('/api/v1/sync/embeddings/raw')

        assert response.status_code == 404

    def test_removed_legacy_check_endpoint_returns_404(self, client):
        response = client.get('/api/v1/sync/check')

        assert response.status_code == 404

    def test_removed_legacy_data_endpoint_returns_404(self, client):
        response = client.get('/api/v1/sync/data')

        assert response.status_code == 404
