"""Smoke and HTML contract tests for admin panel pages."""
from __future__ import annotations

from html.parser import HTMLParser


class AdminHTMLParser(HTMLParser):
    """Collect a small, dependency-free view of rendered admin HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.scripts: set[str] = set()
        self.hrefs: set[str] = set()
        self.forms: dict[str, dict[str, str]] = {}
        self.inputs: dict[str, dict[str, str]] = {}
        self.tags_by_id: dict[str, str] = {}
        self.classes: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        element_id = attr_map.get("id")

        if element_id:
            self.ids.add(element_id)
            self.tags_by_id[element_id] = tag

        for class_name in attr_map.get("class", "").split():
            self.classes.add(class_name)

        if tag == "script" and "src" in attr_map:
            self.scripts.add(attr_map["src"])
        elif tag == "a" and "href" in attr_map:
            self.hrefs.add(attr_map["href"])
        elif tag == "form" and element_id:
            self.forms[element_id] = attr_map
        elif tag == "input" and element_id:
            self.inputs[element_id] = attr_map


def _parse_response(response) -> tuple[str, AdminHTMLParser]:
    html = response.get_data(as_text=True)
    parser = AdminHTMLParser()
    parser.feed(html)
    return html, parser


def _assert_admin_nav(parser: AdminHTMLParser) -> None:
    assert "navbar" in parser.classes
    assert "/admin/dashboard" in parser.hrefs
    assert "/admin/signs" in parser.hrefs
    assert "/admin/categories" in parser.hrefs
    assert "/admin/synonyms" in parser.hrefs
    assert "/admin/lessons" in parser.hrefs


def _assert_dom_ids(parser: AdminHTMLParser, expected_ids: set[str]) -> None:
    missing_ids = expected_ids - parser.ids
    assert not missing_ids, f"Missing DOM ids: {sorted(missing_ids)}"


def test_admin_login_page_contract(client):
    response = client.get("/admin/login")

    assert response.status_code == 200
    html, parser = _parse_response(response)

    assert "loginForm" in parser.forms
    assert parser.inputs["username"]["name"] == "username"
    assert parser.inputs["username"]["type"] == "text"
    assert parser.inputs["password"]["name"] == "password"
    assert parser.inputs["password"]["type"] == "password"
    assert "errorMessage" in parser.ids
    assert "/api/v1/admin/auth/login" in html
    assert "localStorage.setItem('authToken'" in html
    assert "window.location.href = '/admin/dashboard'" in html


def test_admin_dashboard_page_contract(client):
    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    html, parser = _parse_response(response)

    _assert_admin_nav(parser)
    assert "/static/js/common.js" in parser.scripts
    assert "checkAuth()" in html
    assert {"/admin/signs", "/admin/categories", "/admin/lessons"} <= parser.hrefs


def test_admin_signs_page_contract_smoke(client):
    response = client.get("/admin/signs")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    _assert_admin_nav(parser)
    assert "/static/js/common.js" in parser.scripts
    assert "/static/js/signs.js" in parser.scripts
    _assert_dom_ids(
        parser,
        {
            "searchInput",
            "categoryFilter",
            "signsTable",
            "signsTableBody",
            "pagination",
            "signModal",
            "signForm",
            "videoFieldsContainer",
            "editSignModal",
            "editSignForm",
            "videosTableBody",
            "synonymsTableBody",
            "videoModal",
            "synonymModal",
            "viewVideoModal",
            "deleteSignModal",
        },
    )


def test_admin_categories_page_contract(client):
    response = client.get("/admin/categories")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    _assert_admin_nav(parser)
    assert "/static/js/common.js" in parser.scripts
    assert "/static/js/categories.js" in parser.scripts
    _assert_dom_ids(
        parser,
        {
            "categoriesTable",
            "categoriesTableBody",
            "categoryModal",
            "categoryForm",
            "categoryName",
            "categoryOrder",
            "categoryFormError",
            "deleteCategoryConfirmModal",
            "deleteCategoryModal",
            "categoryDetailsModal",
            "categoryDetailsSignsBody",
            "signDetailsModal",
            "signDetailsVideosBody",
            "signDetailsSynonyms",
            "viewSignVideoModal",
        },
    )


def test_admin_synonyms_page_contract(client):
    response = client.get("/admin/synonyms")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    _assert_admin_nav(parser)
    assert "/static/js/common.js" in parser.scripts
    assert "/static/js/synonyms.js" in parser.scripts
    _assert_dom_ids(
        parser,
        {
            "searchInput",
            "synonymsTable",
            "synonymsTableBody",
            "pagination",
            "deleteSynonymModal",
            "deleteSynonymPairDisplay",
            "deleteSynonymError",
            "confirmDeleteSynonymButton",
        },
    )


def test_admin_lessons_page_contract(client):
    response = client.get("/admin/lessons")

    assert response.status_code == 200
    _, parser = _parse_response(response)

    _assert_admin_nav(parser)
    assert "/static/js/common.js" in parser.scripts
    assert "/static/js/lessons.js" in parser.scripts
    _assert_dom_ids(
        parser,
        {
            "lessonsTable",
            "lessonsTableBody",
            "lessonModal",
            "lessonForm",
            "lessonId",
            "lessonTitle",
            "lessonDescription",
            "lessonVideoPreviewGroup",
            "lessonVideoFile",
            "lessonVideoUploadButton",
            "lessonVideoUploadError",
            "lessonOrder",
            "lessonFormError",
            "deleteLessonModal",
            "deleteVideoModal",
            "viewLessonVideoModal",
        },
    )
