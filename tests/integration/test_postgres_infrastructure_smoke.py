"""Smoke checks for PostgreSQL integration fixtures."""
from app.models.category import Category


def test_postgres_transaction_fixture_supports_commit(app_postgres, db_session_postgres):
    """Integration session должна переживать commit внутри теста."""
    category = Category(id="pg_smoke", name="Postgres Smoke", order=1)
    db_session_postgres.add(category)
    db_session_postgres.commit()

    with app_postgres.app_context():
        saved = Category.query.get("pg_smoke")

    assert saved is not None
    assert saved.name == "Postgres Smoke"
