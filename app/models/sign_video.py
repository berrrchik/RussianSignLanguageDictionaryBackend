"""
Модель видео для жеста.
"""
from datetime import datetime
from app.database import db
from app.utils.formatters import format_datetime


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
        # Гарантируем наличие context_description
        context_desc = self.context_description
        if not context_desc or (isinstance(context_desc, str) and context_desc.strip() == ''):
            context_desc = f"Видео {self.order + 1}" if self.order > 0 else "Основное видео"
        
        return {
            'id': self.id,
            'url': self.url,
            'context_description': context_desc,
            'order': self.order,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }
    
    def to_dict_local(self):
        """Преобразование в словарь для JSON с полным URL для локального хранилища."""
        from flask import current_app
        
        context_desc = self.context_description
        if not context_desc or (isinstance(context_desc, str) and context_desc.strip() == ''):
            context_desc = f"Видео {self.order + 1}" if self.order > 0 else "Основное видео"
        
        # Строим полный URL: VIDEO_BASE_URL + file_path
        video_base_url = current_app.config.get('VIDEO_BASE_URL', 'http://localhost:5001/videos')
        # Убираем ведущий слэш из file_path, если есть, чтобы избежать двойного слэша
        path = self.file_path.lstrip('/')
        full_url = f"{video_base_url.rstrip('/')}/{path}"
        
        return {
            'id': self.id,
            'url': full_url,
            'context_description': context_desc,
            'order': self.order,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }
    
    def __repr__(self):
        return f'<SignVideo {self.id}: {self.sign_id}>'

