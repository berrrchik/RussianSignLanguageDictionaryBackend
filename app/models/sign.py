"""
Модель жеста.
"""
from datetime import datetime
from app.database import db
from app.utils.formatters import format_datetime


class Sign(db.Model):
    """Модель жеста."""
    
    __tablename__ = 'signs'
    
    id = db.Column(db.String(50), primary_key=True)
    word = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.String(50), db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=False)
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
            'videos_count': len(self.videos) if self.videos else 0,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }
    
    def to_dict_with_relations(self):
        """Преобразование в словарь для JSON с видео и синонимами."""
        from app.models.sign_synonym import SignSynonym
        
        synonyms_query = SignSynonym.query.filter(
            (SignSynonym.sign_id_1 == self.id) | (SignSynonym.sign_id_2 == self.id)
        ).all()
        
        seen_ids = set()
        synonyms = []
        for synonym in synonyms_query:
            other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == self.id else synonym.sign_id_1
            if other_sign_id in seen_ids:
                continue
            seen_ids.add(other_sign_id)
            
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
            'videos': [video.to_dict_local() for video in self.videos],
            'synonyms': synonyms,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }
    
    def __repr__(self):
        return f'<Sign {self.id}: {self.word}>'

