"""
Модель администратора.
"""
from datetime import datetime
from app.database import db
from app.utils.formatters import format_datetime


class AdminUser(db.Model):
    """Модель администратора системы."""
    
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        """Преобразование в словарь для JSON (без пароля)."""
        return {
            'id': self.id,
            'username': self.username,
            'created_at': format_datetime(self.created_at),
            'last_login': format_datetime(self.last_login),
        }
    
    def __repr__(self):
        return f'<AdminUser {self.id}: {self.username}>'

