"""
Модель урока (обучающего видеоматериала).
"""
from datetime import datetime
from app.database import db
from app.utils.serializers import serialize_datetime


class Lesson(db.Model):
    """Модель урока."""
    
    __tablename__ = 'lessons'
    
    id = db.Column(db.String(50), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Преобразование в словарь для JSON (с Unix timestamp для raw endpoints)."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'video_url': self.video_url,
            'order': self.order,
            'created_at': serialize_datetime(self.created_at),
            'updated_at': serialize_datetime(self.updated_at),
        }
    
    def to_dict_with_timestamps(self):
        """Преобразование в словарь для JSON с Unix timestamp (совместимость с API)."""
        return self.to_dict()
    
    def __repr__(self):
        return f'<Lesson {self.id}: {self.title}>'
