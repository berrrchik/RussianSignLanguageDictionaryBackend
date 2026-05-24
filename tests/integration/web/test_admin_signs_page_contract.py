"""Detailed DOM contract for the signs admin page and signs.js."""
from __future__ import annotations

from tests.integration.web.test_admin_pages import _parse_response


def _attrs(parser, element_id: str) -> dict[str, str]:
    return parser.inputs.get(element_id) or parser.forms.get(element_id) or {}


def test_signs_page_exposes_sign_form_contract(client):
    response = client.get("/admin/signs")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    assert parser.forms["signForm"]["onsubmit"] == "saveSign(event)"
    assert _attrs(parser, "signId")["type"] == "hidden"
    assert _attrs(parser, "signWord")["name"] == "word"
    assert parser.tags_by_id["signDescription"] == "textarea"
    assert parser.tags_by_id["signCategory"] == "select"
    assert _attrs(parser, "signKeywords")["name"] == "keywords"
    assert parser.tags_by_id["videoFieldsContainer"] == "div"
    assert parser.tags_by_id["signFormError"] == "div"
    assert parser.tags_by_id["signFormSubmit"] == "button"


def test_signs_page_exposes_edit_modal_video_and_synonym_contracts(client):
    response = client.get("/admin/signs")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    assert "editSignModal" in parser.ids
    assert "editSignContent" in parser.ids
    assert parser.forms["editSignForm"]["onsubmit"] == "updateSign(event)"
    assert _attrs(parser, "editSignId")["type"] == "hidden"
    assert parser.tags_by_id["editSignWord"] == "input"
    assert parser.tags_by_id["editSignDescription"] == "textarea"
    assert parser.tags_by_id["editSignCategory"] == "select"
    assert parser.tags_by_id["videosTableBody"] == "tbody"
    assert parser.tags_by_id["synonymsTableBody"] == "tbody"
    assert parser.tags_by_id["signDeleteButton"] == "button"


def test_signs_page_exposes_video_management_contract(client):
    response = client.get("/admin/signs")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    assert parser.forms["videoForm"]["onsubmit"] == "uploadVideo(event)"
    assert _attrs(parser, "videoFile")["type"] == "file"
    assert _attrs(parser, "videoFile")["accept"] == "video/mp4"
    assert parser.tags_by_id["videoContextDescription"] == "textarea"
    assert _attrs(parser, "videoOrder")["type"] == "number"
    assert parser.tags_by_id["videoFormError"] == "div"

    assert parser.forms["editVideoForm"]["onsubmit"] == "saveVideoChanges(event)"
    assert parser.tags_by_id["editVideoContextDescription"] == "textarea"
    assert _attrs(parser, "editVideoOrder")["type"] == "number"
    assert parser.tags_by_id["editVideoFormError"] == "div"
    assert parser.tags_by_id["viewVideoPlayer"] == "video"
    assert parser.tags_by_id["viewVideoDescription"] == "p"


def test_signs_page_exposes_synonym_and_delete_confirmation_contracts(client):
    response = client.get("/admin/signs")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    assert parser.tags_by_id["synonymSearch"] == "input"
    assert _attrs(parser, "synonymSearch")["onkeyup"] == "searchSignsForSynonym(this.value)"
    assert parser.tags_by_id["synonymSearchResults"] == "div"
    assert parser.tags_by_id["synonymFormError"] == "div"

    assert parser.tags_by_id["deleteSignWordDisplay"] == "span"
    assert parser.tags_by_id["deleteSignConfirmInput"] == "input"
    assert parser.tags_by_id["deleteSignError"] == "div"
    assert parser.tags_by_id["confirmDeleteSignButton"] == "button"
