"""
Pydantic response модели для /raw эндпоинтов.

Эти модели используют Unix timestamp (секунды) для дат и
предназначены для упрощенных эндпоинтов без обертки {success, data, message}.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_serializer

from app.utils.serializers import serialize_datetime


class SignVideoRawResponse(BaseModel):
    """Response модель для видео жеста."""
    
    id: int
    url: str
    context_description: str
    order: int
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime) -> Optional[int]:
        return serialize_datetime(dt)
    
    model_config = {"from_attributes": True}


class SynonymRawResponse(BaseModel):
    """Response модель для синонима жеста."""
    
    id: str
    word: str
    
    model_config = {"from_attributes": True}


class SignRawResponse(BaseModel):
    """Response модель для жеста с видео и синонимами."""
    
    id: str
    word: str
    description: Optional[str] = None
    category_id: str
    videos: List[SignVideoRawResponse]
    synonyms: List[SynonymRawResponse]
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime) -> Optional[int]:
        return serialize_datetime(dt)
    
    model_config = {"from_attributes": True}


class CategoryRawResponse(BaseModel):
    """Response модель для категории."""
    
    id: str
    name: str
    order: int
    sign_count: int
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime) -> Optional[int]:
        return serialize_datetime(dt)
    
    model_config = {"from_attributes": True}


class SyncMetadataRawResponse(BaseModel):
    """Response модель для метаданных синхронизации."""
    
    last_updated: datetime
    has_updates: bool
    
    @field_serializer('last_updated')
    def serialize_dt(self, dt: datetime) -> Optional[int]:
        return serialize_datetime(dt)
    
    model_config = {"from_attributes": True}


class SyncDataRawResponse(BaseModel):
    """Response модель для полных данных синхронизации."""
    
    categories: List[CategoryRawResponse]
    signs: List[SignRawResponse]
    last_updated: datetime
    
    @field_serializer('last_updated')
    def serialize_dt(self, dt: datetime) -> Optional[int]:
        return serialize_datetime(dt)
    
    model_config = {"from_attributes": True}


class ErrorRawResponse(BaseModel):
    """Response модель для ошибок в /raw эндпоинтах."""
    
    error: str
    message: str
