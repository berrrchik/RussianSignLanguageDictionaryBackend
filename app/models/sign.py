"""
Модель жеста.
"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.database import db


class Sign(db.Model):
    """Модель жеста."""
    
    __tablename__ = 'signs'
    
    id = db.Column(db.String(50), primary_key=True)
    word = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.String(50), db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=False)
    embeddings = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    videos = db.relationship('SignVideo', backref='sign', lazy=True, cascade='all, delete-orphan', order_by='SignVideo.order')
    
    def to_dict(self):
        """Преобразование в словарь для JSON (без связей)."""
        return {
            'id': self.id,
            'word': self.word,
            'description': self.description,
            'category_id': self.category_id,
            'embeddings': self.embeddings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_dict_with_relations(self):
        """Преобразование в словарь для JSON с видео и синонимами."""
        from app.models.sign_synonym import SignSynonym
        
        # Получение синонимов (через sign_id_1 или sign_id_2)
        synonyms_query = SignSynonym.query.filter(
            (SignSynonym.sign_id_1 == self.id) | (SignSynonym.sign_id_2 == self.id)
        ).all()
        
        synonyms = []
        for synonym in synonyms_query:
            # Определяем ID другого жеста
            other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == self.id else synonym.sign_id_1
            other_sign = Sign.query.get(other_sign_id)
            if other_sign:
                synonyms.append({
                    'id': other_sign.id,
                    'word': other_sign.word
                })
        
        return {
            'id': self.id,
            'word': self.word,
            'description': self.description,
            'category_id': self.category_id,
            'videos': [video.to_dict() for video in self.videos],
            'synonyms': synonyms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<Sign {self.id}: {self.word}>'

