"""
Модель категории жестов.
"""
from datetime import datetime
from app.database import db
from app.utils.formatters import format_datetime


class Category(db.Model):
    """Модель категории жестов."""
    
    __tablename__ = 'categories'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    signs = db.relationship('Sign', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Преобразование в словарь для JSON."""
        return {
            'id': self.id,
            'name': self.name,
            'order': self.order,
            'sign_count': len(self.signs) if self.signs else 0,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }
    
    def __repr__(self):
        return f'<Category {self.id}: {self.name}>'

