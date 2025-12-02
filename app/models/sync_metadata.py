"""
Модель метаданных синхронизации.
"""
from datetime import datetime
from app.database import db


class SyncMetadata(db.Model):
    """Модель метаданных для синхронизации мобильного приложения."""
    
    __tablename__ = 'sync_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    version = db.Column(db.Integer, default=1)
    
    def to_dict(self):
        """Преобразование в словарь для JSON."""
        return {
            'id': self.id,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'version': self.version,
        }
    
    def __repr__(self):
        return f'<SyncMetadata: last_updated={self.last_updated}>'

