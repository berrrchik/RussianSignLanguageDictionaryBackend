"""
Модель связи синонимов между жестами.
"""
from datetime import datetime
from app.database import db
from app.utils.formatters import format_datetime


class SignSynonym(db.Model):
    """Модель двусторонней связи синонимов между жестами."""
    
    __tablename__ = 'sign_synonyms'
    
    id = db.Column(db.Integer, primary_key=True)
    sign_id_1 = db.Column(db.String(50), db.ForeignKey('signs.id', ondelete='CASCADE'), nullable=False)
    sign_id_2 = db.Column(db.String(50), db.ForeignKey('signs.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальность пары (sign_id_1, sign_id_2)
    __table_args__ = (
        db.UniqueConstraint('sign_id_1', 'sign_id_2', name='unique_synonym_pair'),
        db.CheckConstraint('sign_id_1 != sign_id_2', name='check_different_signs'),
    )
    
    def to_dict(self):
        """Преобразование в словарь для JSON."""
        return {
            'id': self.id,
            'sign_id_1': self.sign_id_1,
            'sign_id_2': self.sign_id_2,
            'created_at': format_datetime(self.created_at),
        }
    
    def __repr__(self):
        return f'<SignSynonym {self.id}: {self.sign_id_1} <-> {self.sign_id_2}>'

