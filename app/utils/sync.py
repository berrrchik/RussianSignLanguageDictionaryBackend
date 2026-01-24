"""
Утилиты для синхронизации данных.
"""
from datetime import datetime
from app.database import db
from app.models.sync_metadata import SyncMetadata


def get_or_create_sync_metadata() -> SyncMetadata:
    """
    Получает или создает метаданные синхронизации.
    
    Returns:
        SyncMetadata объект
    """
    metadata = SyncMetadata.query.first()
    if not metadata:
        metadata = SyncMetadata(last_updated=datetime.utcnow())
        db.session.add(metadata)
        db.session.commit()
    return metadata


def update_sync_metadata():
    """
    Обновляет метаданные синхронизации (last_updated).
    
    Вызывается после любых изменений в таблицах signs, categories, sign_videos, sign_synonyms, lessons.
    """
    metadata = SyncMetadata.query.first()
    if metadata:
        metadata.last_updated = datetime.utcnow()
    else:
        metadata = SyncMetadata(last_updated=datetime.utcnow())
        db.session.add(metadata)
    db.session.commit()

