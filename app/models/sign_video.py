"""
Модель видео для жеста.
"""
from datetime import datetime
from app.database import db


class SignVideo(db.Model):
    """Модель видео для жеста."""
    
    __tablename__ = 'sign_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    sign_id = db.Column(db.String(50), db.ForeignKey('signs.id', ondelete='CASCADE'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    context_description = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Преобразование в словарь для JSON."""
        return {
            'id': self.id,
            'url': self.url,
            'context_description': self.context_description,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<SignVideo {self.id}: {self.sign_id}>'

