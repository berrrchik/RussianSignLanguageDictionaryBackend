"""Тесты модели SignSynonym и связанных ограничений."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym


def _create_sign_graph():
    category = Category(id="cat_1", name="Категория", order=1)
    sign_a = Sign(id="sign_a", word="А", category_id="cat_1")
    sign_b = Sign(id="sign_b", word="Б", category_id="cat_1")
    sign_c = Sign(id="sign_c", word="В", category_id="cat_1")
    db.session.add_all([category, sign_a, sign_b, sign_c])
    db.session.commit()


def test_sign_synonym_to_dict_serializes_fields(app_ctx):
    _create_sign_graph()
    synonym = SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b")
    db.session.add(synonym)
    db.session.commit()

    payload = synonym.to_dict()

    assert payload["id"] == synonym.id
    assert payload["sign_id_1"] == "sign_a"
    assert payload["sign_id_2"] == "sign_b"
    assert payload["created_at"].endswith("Z")


def test_sign_synonym_rejects_self_reference(app_ctx):
    _create_sign_graph()
    db.session.add(SignSynonym(sign_id_1="sign_a", sign_id_2="sign_a"))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_sign_synonym_rejects_duplicate_pair(app_ctx):
    _create_sign_graph()
    db.session.add(SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"))
    db.session.commit()
    db.session.add(SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_sign_synonym_allows_reverse_direction_pair(app_ctx):
    _create_sign_graph()
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign_a", sign_id_2="sign_b"),
            SignSynonym(sign_id_1="sign_b", sign_id_2="sign_a"),
        ]
    )
    db.session.commit()

    saved_pairs = SignSynonym.query.order_by(SignSynonym.id).all()

    assert [(item.sign_id_1, item.sign_id_2) for item in saved_pairs] == [
        ("sign_a", "sign_b"),
        ("sign_b", "sign_a"),
    ]
