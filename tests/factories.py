"""Небольшие фабрики тестовых данных для pytest."""
from __future__ import annotations

from datetime import datetime

import bcrypt

from app.database import db
from app.models.admin_user import AdminUser
from app.models.category import Category
from app.models.lesson import Lesson
from app.models.sign import Sign
from app.models.sign_video import SignVideo
from app.models.sync_metadata import SyncMetadata


def _persist(instance, *, commit: bool):
    db.session.add(instance)
    if commit:
        db.session.commit()
    return instance


def create_admin_user(
    *,
    username: str = "testadmin",
    password: str = "testpass",
    commit: bool = True,
    **overrides,
) -> AdminUser:
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return _persist(
        AdminUser(username=username, password_hash=password_hash, **overrides),
        commit=commit,
    )


def create_category(
    *,
    category_id: str = "category_1",
    name: str = "Test Category",
    order: int = 1,
    commit: bool = True,
    **overrides,
) -> Category:
    return _persist(
        Category(id=category_id, name=name, order=order, **overrides),
        commit=commit,
    )


def create_sign(
    *,
    sign_id: str = "sign_1",
    word: str = "тест",
    category_id: str,
    description: str | None = None,
    commit: bool = True,
    **overrides,
) -> Sign:
    return _persist(
        Sign(
            id=sign_id,
            word=word,
            description=description,
            category_id=category_id,
            **overrides,
        ),
        commit=commit,
    )


def create_sign_video(
    *,
    sign_id: str,
    video_id: int | None = None,
    file_path: str = "signs/test/video.mp4",
    url: str = "http://testserver.local/videos/signs/test/video.mp4",
    context_description: str = "Основное видео",
    order: int = 0,
    commit: bool = True,
    **overrides,
) -> SignVideo:
    payload = {
        "sign_id": sign_id,
        "file_path": file_path,
        "url": url,
        "context_description": context_description,
        "order": order,
        **overrides,
    }
    if video_id is not None:
        payload["id"] = video_id

    return _persist(SignVideo(**payload), commit=commit)


def create_lesson(
    *,
    lesson_id: str = "lesson_1",
    title: str = "Урок 1",
    description: str = "Описание урока",
    video_url: str = "lessons/lesson-1.mp4",
    order: int = 1,
    commit: bool = True,
    **overrides,
) -> Lesson:
    return _persist(
        Lesson(
            id=lesson_id,
            title=title,
            description=description,
            video_url=video_url,
            order=order,
            **overrides,
        ),
        commit=commit,
    )


def create_sync_metadata(
    *,
    last_updated: datetime | None = None,
    version: int = 1,
    commit: bool = True,
    **overrides,
) -> SyncMetadata:
    return _persist(
        SyncMetadata(
            last_updated=last_updated or datetime.utcnow(),
            version=version,
            **overrides,
        ),
        commit=commit,
    )
