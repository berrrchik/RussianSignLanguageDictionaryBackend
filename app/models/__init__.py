"""
SQLAlchemy модели для системы управления словарём.
"""
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.models.sign_synonym import SignSynonym
from app.models.sync_metadata import SyncMetadata
from app.models.admin_user import AdminUser

__all__ = [
    'Category',
    'Sign',
    'SignVideo',
    'SignSynonym',
    'SyncMetadata',
    'AdminUser',
]

