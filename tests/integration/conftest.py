"""Integration-layer fixtures."""
from __future__ import annotations

import os
from typing import Callable

import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.config import Config
from app.database import db


def _assert_test_database_url(database_uri: str) -> None:
    """Страховка от запуска integration-тестов против dev/prod БД."""
    database_name = make_url(database_uri).database or ""
    if "test" not in database_name and "pytest" not in database_name:
        raise pytest.UsageError(
            "Integration DB must point to a dedicated test database. "
            f"Got database name: {database_name!r}"
        )


@pytest.fixture(autouse=True)
def _reset_sbert_search_service(reset_sbert_singleton):
    """Не даёт singleton SBERT протекать между integration-тестами."""
    yield


@pytest.fixture(scope="session")
def postgres_database_uri() -> str:
    """URL отдельной PostgreSQL базы для integration-тестов."""
    database_uri = os.getenv("TEST_DATABASE_URL") or os.getenv("TEST_POSTGRES_URL")
    if not database_uri:
        pytest.skip("Set TEST_DATABASE_URL or TEST_POSTGRES_URL to run PostgreSQL integration tests.")

    _assert_test_database_url(database_uri)
    return database_uri


@pytest.fixture(scope="session")
def postgres_schema(
    postgres_database_uri: str,
    test_config_factory: Callable[..., type[Config]],
    tmp_path_factory: pytest.TempPathFactory,
):
    """Поднимает схему в PostgreSQL один раз на сессию."""
    storage_path = tmp_path_factory.mktemp("postgres-video-storage")
    test_config = test_config_factory(
        database_uri=postgres_database_uri,
        video_storage_path=str(storage_path),
        video_base_url="http://testserver.local/videos",
    )
    app = create_app(test_config)

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_postgres(
    monkeypatch: pytest.MonkeyPatch,
    postgres_schema,
    postgres_database_uri: str,
    test_config_factory: Callable[..., type[Config]],
    tmp_video_storage_config: dict[str, str],
):
    """Flask app, работающий поверх PostgreSQL test DB."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_uri)

    test_config = test_config_factory(
        database_uri=postgres_database_uri,
        video_storage_path=tmp_video_storage_config["VIDEO_STORAGE_PATH"],
        video_base_url=tmp_video_storage_config["VIDEO_BASE_URL"],
    )
    app = create_app(test_config)

    with app.app_context():
        yield app
        db.session.remove()


@pytest.fixture
def db_session_postgres(app_postgres):
    """Транзакционная SQLAlchemy session с rollback после теста."""
    connection = db.engine.connect()
    transaction = connection.begin()

    session = scoped_session(sessionmaker(bind=connection))
    session_instance = session()
    session_instance.begin_nested()

    @event.listens_for(session_instance, "after_transaction_end")
    def restart_savepoint(session_, trans) -> None:
        parent = getattr(trans, "parent", None)
        if trans.nested and (parent is None or not parent.nested):
            session_.begin_nested()

    previous_session = db.session
    db.session = session

    try:
        yield session
    finally:
        db.session = previous_session
        try:
            if event.contains(session_instance, "after_transaction_end", restart_savepoint):
                event.remove(session_instance, "after_transaction_end", restart_savepoint)
        finally:
            session.remove()
            transaction.rollback()
            connection.close()


@pytest.fixture
def client_postgres(app_postgres, db_session_postgres):
    """Flask test client поверх PostgreSQL app."""
    return app_postgres.test_client()
