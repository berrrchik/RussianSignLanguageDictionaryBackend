"""
Утилиты для синхронизации данных.
"""
from datetime import datetime
from app.database import db
from app.models.sync_metadata import SyncMetadata


def update_sync_metadata():
    """
    Обновляет метаданные синхронизации (last_updated).
    
    Вызывается после любых изменений в таблицах signs, categories, sign_videos, sign_synonyms.
    """
    metadata = SyncMetadata.query.first()
    if metadata:
        metadata.last_updated = datetime.utcnow()
    else:
        metadata = SyncMetadata(last_updated=datetime.utcnow())
        db.session.add(metadata)
    db.session.commit()

