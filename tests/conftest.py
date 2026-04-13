"""Общие pytest fixtures для всех тестовых слоёв."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.config import Config
from app.database import db
from app.models.admin_user import AdminUser
from app.utils.auth import generate_token
from tests import factories


TEST_ENV_DEFAULTS = {
    "FLASK_ENV": "testing",
    "FLASK_DEBUG": "False",
    "PRELOAD_SBERT": "false",
    "JWT_SECRET_KEY": "test-secret-key",
    "JWT_EXPIRATION_DELTA": "3600",
    "SECRET_KEY": "test-secret-key",
    "VIDEO_STORAGE_TYPE": "local",
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "SUPABASE_SERVICE_ROLE_KEY": "",
    "SUPABASE_BUCKET": "signs",
    "SUPABASE_LESSONS_BUCKET": "lessons",
}


def _sqlite_engine_options() -> dict[str, Any]:
    return {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Изолирует env vars, которые читаются через os.getenv."""
    for key, value in TEST_ENV_DEFAULTS.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def tmp_video_storage_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> dict[str, str]:
    """Конфиг локального video storage на временной директории."""
    storage_path = tmp_path / "videos"
    config = {
        "VIDEO_STORAGE_TYPE": "local",
        "VIDEO_STORAGE_PATH": str(storage_path),
        "VIDEO_BASE_URL": "http://testserver.local/videos",
    }

    for key, value in config.items():
        monkeypatch.setenv(key, value)

    return config


@pytest.fixture(scope="session")
def test_config_factory() -> Callable[..., type[Config]]:
    """Строит test config class с нужной БД и storage-настройками."""

    def factory(
        *,
        database_uri: str,
        video_storage_path: str,
        video_base_url: str,
        config_overrides: dict[str, Any] | None = None,
    ) -> type[Config]:
        attrs: dict[str, Any] = {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": TEST_ENV_DEFAULTS["JWT_SECRET_KEY"],
            "JWT_EXPIRATION_DELTA": int(TEST_ENV_DEFAULTS["JWT_EXPIRATION_DELTA"]),
            "SECRET_KEY": TEST_ENV_DEFAULTS["SECRET_KEY"],
            "VIDEO_STORAGE_TYPE": "local",
            "VIDEO_STORAGE_PATH": video_storage_path,
            "VIDEO_BASE_URL": video_base_url,
        }

        if database_uri.startswith("sqlite"):
            attrs["SQLALCHEMY_ENGINE_OPTIONS"] = _sqlite_engine_options()
        else:
            attrs["SQLALCHEMY_ENGINE_OPTIONS"] = dict(Config.SQLALCHEMY_ENGINE_OPTIONS)

        if config_overrides:
            attrs.update(config_overrides)

        return type("TestConfig", (Config,), attrs)

    return factory


@pytest.fixture
def app_sqlite(
    monkeypatch: pytest.MonkeyPatch,
    test_config_factory: Callable[..., type[Config]],
    tmp_video_storage_config: dict[str, str],
):
    """Flask app с in-memory SQLite для unit/e2e и быстрых integration smoke."""
    database_uri = "sqlite://"
    monkeypatch.setenv("DATABASE_URL", database_uri)

    test_config = test_config_factory(
        database_uri=database_uri,
        video_storage_path=tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        video_base_url=tmp_video_storage_config["VIDEO_BASE_URL"],
    )
    app = create_app(test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app(app_sqlite):
    """Совместимость со старыми тестами и единая точка входа для SQLite."""
    return app_sqlite


@pytest.fixture
def client(app_sqlite):
    """Flask test client поверх SQLite app."""
    return app_sqlite.test_client()


@pytest.fixture
def app_ctx(app_sqlite):
    """Явный app context для фабрик и прямой работы с моделями."""
    with app_sqlite.app_context():
        yield


@pytest.fixture
def db_session(app_ctx):
    """SQLAlchemy session для SQLite-based тестов."""
    yield db.session
    db.session.remove()


@pytest.fixture
def admin_user(app_ctx):
    """Тестовый администратор с реальным bcrypt hash."""
    return factories.create_admin_user()


@pytest.fixture
def admin_user_factory(app_ctx):
    """Фабрика для создания администраторов с bcrypt hash."""
    return factories.create_admin_user


@pytest.fixture
def category_factory(app_ctx):
    """Фабрика категорий для будущих тестов."""
    return factories.create_category


@pytest.fixture
def sign_factory(app_ctx):
    """Фабрика жестов для будущих тестов."""
    return factories.create_sign


@pytest.fixture
def sign_video_factory(app_ctx):
    """Фабрика видео жестов для будущих тестов."""
    return factories.create_sign_video


@pytest.fixture
def lesson_factory(app_ctx):
    """Фабрика уроков для будущих тестов."""
    return factories.create_lesson


@pytest.fixture
def sync_metadata_factory(app_ctx):
    """Фабрика sync metadata для будущих тестов."""
    return factories.create_sync_metadata


@pytest.fixture
def auth_token(app_sqlite, admin_user: AdminUser) -> str:
    """JWT для тестового администратора."""
    return generate_token(
        admin_user.id,
        app_sqlite.config["JWT_SECRET_KEY"],
        app_sqlite.config["JWT_EXPIRATION_DELTA"],
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization headers для admin endpoints."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def reset_sbert_singleton():
    """Сбрасывает singleton SBERTSearchService до и после теста."""
    from app.services import sbert_search_service

    sbert_search_service._sbert_search_service = None
    yield
    sbert_search_service._sbert_search_service = None


def pytest_configure(config: pytest.Config) -> None:
    """Регистрирует маркеры тестовых слоёв."""
    config.addinivalue_line("markers", "unit: быстрые unit-тесты без внешней БД")
    config.addinivalue_line("markers", "integration: интеграционные тесты Flask/DB/PostgreSQL")
    config.addinivalue_line("markers", "e2e: end-to-end сценарии приложения")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Автоматически помечает тесты по каталогу."""
    for item in items:
        path_parts = Path(str(item.fspath)).parts
        if "unit" in path_parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in path_parts:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in path_parts:
            item.add_marker(pytest.mark.e2e)
