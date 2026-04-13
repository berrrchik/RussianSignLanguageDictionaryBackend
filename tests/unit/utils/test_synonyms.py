"""Unit tests for synonym helpers."""
from __future__ import annotations

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym
from app.utils.synonyms import (
    check_synonym_exists,
    create_synonym_relation,
    delete_synonym_relation,
    get_sign_synonyms,
)


def _seed_signs():
    category = Category(id="cat_1", name="Категория", order=1)
    sign_a = Sign(id="sign_a", word="А", category_id="cat_1")
    sign_b = Sign(id="sign_b", word="Б", category_id="cat_1")
    sign_c = Sign(id="sign_c", word="В", category_id="cat_1")
    db.session.add_all([category, sign_a, sign_b, sign_c])
    db.session.commit()


def test_get_sign_synonyms_returns_synonyms_from_both_directions(app_ctx):
    _seed_signs()
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"),
            SignSynonym(sign_id_1="sign_c", sign_id_2="sign_a"),
        ]
    )
    db.session.commit()

    synonyms = get_sign_synonyms("sign_a")

    assert synonyms == [
        {"id": "sign_b", "word": "Б"},
        {"id": "sign_c", "word": "В"},
    ]


def test_get_sign_synonyms_deduplicates_bidirectional_duplicates(app_ctx):
    _seed_signs()
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"),
            SignSynonym(sign_id_1="sign_b", sign_id_2="sign_a"),
        ]
    )
    db.session.commit()

    assert get_sign_synonyms("sign_a") == [{"id": "sign_b", "word": "Б"}]


def test_check_synonym_exists_finds_relation_in_both_directions(app_ctx):
    _seed_signs()
    db.session.add(SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"))
    db.session.commit()

    assert check_synonym_exists("sign_a", "sign_b") is True
    assert check_synonym_exists("sign_b", "sign_a") is True


def test_create_synonym_relation_creates_two_records(app_ctx):
    _seed_signs()

    create_synonym_relation("sign_a", "sign_b")
    db.session.commit()

    pairs = {
        (item.sign_id_1, item.sign_id_2)
        for item in SignSynonym.query.all()
    }
    assert pairs == {("sign_a", "sign_b"), ("sign_b", "sign_a")}


def test_delete_synonym_relation_removes_both_records(app_ctx):
    _seed_signs()
    create_synonym_relation("sign_a", "sign_b")
    db.session.commit()

    deleted = delete_synonym_relation("sign_a", "sign_b")
    db.session.commit()

    assert deleted is True
    assert SignSynonym.query.count() == 0


def test_delete_synonym_relation_returns_false_for_missing_relation(app_ctx):
    _seed_signs()

    assert delete_synonym_relation("sign_a", "sign_b") is False
