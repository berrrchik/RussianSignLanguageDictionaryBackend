"""Integration tests for admin synonyms API."""
from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.sign_synonym import SignSynonym
from app.models.sync_metadata import SyncMetadata
from app.constants import MAX_PER_PAGE


def _seed_signs(category_factory, sign_factory):
    category_factory(category_id="cat-a", name="А", order=1)
    sign_factory(sign_id="sign-1", word="арбуз", category_id="cat-a")
    sign_factory(sign_id="sign-2", word="ёж", category_id="cat-a")
    sign_factory(sign_id="sign-3", word="beta", category_id="cat-a")


def _set_old_sync_metadata(sync_metadata_factory):
    return sync_metadata_factory(last_updated=datetime(2025, 1, 1, 0, 0, 0)).last_updated


def _current_sync_updated_at():
    metadata = SyncMetadata.query.first()
    assert metadata is not None
    return metadata.last_updated


def test_list_synonyms_for_sign(client, auth_headers, category_factory, sign_factory):
    _seed_signs(category_factory, sign_factory)
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-2"),
            SignSynonym(sign_id_1="sign-2", sign_id_2="sign-1"),
        ]
    )
    db.session.commit()

    response = client.get("/api/v1/admin/signs/sign-1/synonyms", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["data"] == [{"id": "sign-2", "word": "ёж"}]


def test_global_synonyms_list_deduplicates_bidirectional_pairs_and_clamps_per_page(
    client, auth_headers, category_factory, sign_factory
):
    _seed_signs(category_factory, sign_factory)
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-2"),
            SignSynonym(sign_id_1="sign-2", sign_id_2="sign-1"),
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-3"),
            SignSynonym(sign_id_1="sign-3", sign_id_2="sign-1"),
        ]
    )
    db.session.commit()

    response = client.get("/api/v1/admin/synonyms?per_page=999", headers=auth_headers)

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["pagination"]["per_page"] == MAX_PER_PAGE
    assert payload["pagination"]["total"] == 2
    assert len(payload["synonyms"]) == 2


def test_global_synonyms_search_supports_ids_and_words(client, auth_headers, category_factory, sign_factory):
    _seed_signs(category_factory, sign_factory)
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-3"),
            SignSynonym(sign_id_1="sign-3", sign_id_2="sign-1"),
        ]
    )
    db.session.commit()

    by_word = client.get("/api/v1/admin/synonyms?search=beta", headers=auth_headers)
    by_id = client.get("/api/v1/admin/synonyms?search=sign-3", headers=auth_headers)

    assert by_word.status_code == 200
    assert by_word.get_json()["data"]["pagination"]["total"] == 1
    assert by_id.status_code == 200
    assert by_id.get_json()["data"]["pagination"]["total"] == 1


def test_global_synonyms_search_handles_empty_result(client, auth_headers, category_factory, sign_factory):
    _seed_signs(category_factory, sign_factory)

    response = client.get("/api/v1/admin/synonyms?search=missing", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "synonyms": [],
        "pagination": {"page": 1, "per_page": 50, "total": 0, "pages": 1},
    }


def test_add_synonym_validates_required_and_existing_target(client, auth_headers, category_factory, sign_factory):
    _seed_signs(category_factory, sign_factory)

    missing_field = client.post(
        "/api/v1/admin/signs/sign-1/synonyms",
        headers=auth_headers,
        json={"unexpected": "value"},
    )
    missing_target = client.post(
        "/api/v1/admin/signs/sign-1/synonyms",
        headers=auth_headers,
        json={"synonym_sign_id": "missing"},
    )

    assert missing_field.status_code == 400
    assert missing_field.get_json()["error"]["code"] == "MISSING_FIELD"
    assert missing_target.status_code == 404
    assert missing_target.get_json()["error"]["code"] == "NOT_FOUND"


def test_add_synonym_rejects_self_link_and_duplicate_relation(
    client, auth_headers, category_factory, sign_factory
):
    _seed_signs(category_factory, sign_factory)
    db.session.add_all(
        [
            SignSynonym(sign_id_1="sign-1", sign_id_2="sign-2"),
            SignSynonym(sign_id_1="sign-2", sign_id_2="sign-1"),
        ]
    )
    db.session.commit()

    self_link = client.post(
        "/api/v1/admin/signs/sign-1/synonyms",
        headers=auth_headers,
        json={"synonym_sign_id": "sign-1"},
    )
    duplicate = client.post(
        "/api/v1/admin/signs/sign-1/synonyms",
        headers=auth_headers,
        json={"synonym_sign_id": "sign-2"},
    )

    assert self_link.status_code == 400
    assert self_link.get_json()["error"]["code"] == "INVALID_SYNONYM"
    assert duplicate.status_code == 400
    assert duplicate.get_json()["error"]["code"] == "SYNONYM_EXISTS"


def test_add_synonym_creates_relation_and_updates_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sync_metadata_factory
):
    _seed_signs(category_factory, sign_factory)
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    response = client.post(
        "/api/v1/admin/signs/sign-1/synonyms",
        headers=auth_headers,
        json={"synonym_sign_id": "sign-2"},
    )

    assert response.status_code == 201
    assert SignSynonym.query.count() == 2
    assert _current_sync_updated_at() > previous_sync


def test_delete_synonym_by_pair_and_by_relation_id_updates_sync_metadata(
    client, auth_headers, category_factory, sign_factory, sync_metadata_factory
):
    _seed_signs(category_factory, sign_factory)
    first_pair = [
        SignSynonym(sign_id_1="sign-1", sign_id_2="sign-2"),
        SignSynonym(sign_id_1="sign-2", sign_id_2="sign-1"),
    ]
    db.session.add_all(first_pair)
    db.session.commit()
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)

    by_pair = client.delete("/api/v1/admin/signs/sign-1/synonyms/sign-2", headers=auth_headers)

    assert by_pair.status_code == 200
    assert SignSynonym.query.count() == 0
    assert _current_sync_updated_at() > previous_sync

    second_pair = [
        SignSynonym(sign_id_1="sign-1", sign_id_2="sign-3"),
        SignSynonym(sign_id_1="sign-3", sign_id_2="sign-1"),
    ]
    db.session.add_all(second_pair)
    db.session.commit()
    previous_sync = _set_old_sync_metadata(sync_metadata_factory)
    relation_id = SignSynonym.query.filter_by(sign_id_1="sign-1", sign_id_2="sign-3").first().id

    by_id = client.delete(f"/api/v1/admin/synonyms/{relation_id}", headers=auth_headers)

    assert by_id.status_code == 200
    assert SignSynonym.query.count() == 0
    assert _current_sync_updated_at() > previous_sync
