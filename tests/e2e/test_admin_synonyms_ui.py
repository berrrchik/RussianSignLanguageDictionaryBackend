"""Browser coverage for administrator synonym management."""

from playwright.sync_api import Page, expect


PRIMARY_SIGN_ID = "synonym_primary"
PRIMARY_SIGN_WORD = "Primary Browser Sign"
TARGET_SIGN_ID = "synonym_target"
TARGET_SIGN_WORD = "Target Browser Sign"


def _login(page: Page, live_server: str, e2e_admin: dict[str, str]) -> None:
    page.goto(f"{live_server}/admin/login")
    page.locator("#username").fill(e2e_admin["username"])
    page.locator("#password").fill(e2e_admin["password"])
    page.get_by_role("button", name="Войти").click()
    page.wait_for_url(f"{live_server}/admin/dashboard")


def test_admin_can_add_search_and_delete_synonym_relation(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
    category_factory,
    sign_factory,
) -> None:
    category_factory(category_id="synonym_category", name="Synonym Category", order=1)
    sign_factory(
        sign_id=PRIMARY_SIGN_ID,
        word=PRIMARY_SIGN_WORD,
        category_id="synonym_category",
    )
    sign_factory(
        sign_id=TARGET_SIGN_ID,
        word=TARGET_SIGN_WORD,
        category_id="synonym_category",
    )
    _login(page, live_server, e2e_admin)

    page.goto(f"{live_server}/admin/signs")
    primary_row = page.locator("#signsTableBody tr", has_text=PRIMARY_SIGN_WORD)
    expect(primary_row).to_be_visible()
    primary_row.get_by_role("button", name="Редактировать").click()
    expect(page.locator("#editSignModal")).to_be_visible()

    page.get_by_role("button", name="Добавить синоним").click()
    page.locator("#synonymSearch").press_sequentially("Target Browser")
    expect(page.locator("#synonymSearchResults")).to_contain_text(TARGET_SIGN_WORD)
    with page.expect_response(
        lambda response: response.url.endswith(
            f"/api/v1/admin/signs/{PRIMARY_SIGN_ID}/synonyms"
        )
        and response.request.method == "POST"
    ) as create_relation:
        page.locator("#synonymSearchResults", has_text=TARGET_SIGN_WORD).click()
    assert create_relation.value.status == 201
    expect(page.locator("#synonymsTableBody")).to_contain_text(TARGET_SIGN_WORD)

    page.goto(f"{live_server}/admin/synonyms")
    expect(page.locator("#synonymsTableBody")).to_contain_text(PRIMARY_SIGN_WORD)
    expect(page.locator("#synonymsTableBody")).to_contain_text(TARGET_SIGN_WORD)

    with page.expect_response(
        lambda response: "/api/v1/admin/synonyms?" in response.url
        and "search=Target%20Browser" in response.url
        and response.request.method == "GET"
    ):
        page.locator("#searchInput").press_sequentially("Target Browser")
    expect(page.locator("#synonymsTableBody")).to_contain_text(TARGET_SIGN_WORD)

    page.locator("#synonymsTableBody tr", has_text=TARGET_SIGN_WORD).get_by_role(
        "button", name="Удалить"
    ).click()
    expect(page.locator("#deleteSynonymModal")).to_be_visible()
    with page.expect_response(
        lambda response: "/api/v1/admin/synonyms/" in response.url
        and response.request.method == "DELETE"
    ) as delete_relation:
        page.locator("#confirmDeleteSynonymButton").click()
    assert delete_relation.value.status == 200
    expect(page.locator("#synonymsTableBody")).to_contain_text(
        "Связи синонимов не найдены"
    )
