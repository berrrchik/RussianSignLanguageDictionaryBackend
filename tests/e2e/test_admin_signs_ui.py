"""Browser coverage for the administrator sign editing workflow."""

from pathlib import Path

from playwright.sync_api import Page, expect


CATEGORY_NAME = "Browser Test Category"
CATEGORY_ID = "browser_test_category"
SIGN_WORD = "Browser Test Sign"
UPDATED_SIGN_WORD = "Browser Updated Sign"


def _login(page: Page, live_server: str, e2e_admin: dict[str, str]) -> None:
    page.goto(f"{live_server}/admin/login")
    page.locator("#username").fill(e2e_admin["username"])
    page.locator("#password").fill(e2e_admin["password"])
    page.get_by_role("button", name="Войти").click()
    page.wait_for_url(f"{live_server}/admin/dashboard")


def test_admin_can_create_update_and_delete_sign_with_video(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
    test_mp4: Path,
) -> None:
    _login(page, live_server, e2e_admin)

    page.goto(f"{live_server}/admin/categories")
    page.get_by_role("button", name="Создать категорию").click()
    page.locator("#categoryName").fill(CATEGORY_NAME)
    page.locator("#categoryOrder").fill("1")
    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/admin/categories")
        and response.request.method == "POST"
    ) as create_category:
        page.locator("#categoryFormSubmit").click()
    assert create_category.value.status == 201
    expect(page.locator("#categoriesTableBody")).to_contain_text(CATEGORY_NAME)

    page.goto(f"{live_server}/admin/signs")
    page.get_by_role("button", name="Создать жест").click()
    page.locator("#signWord").fill(SIGN_WORD)
    page.locator("#signDescription").fill("Created in Playwright e2e")
    page.locator("#signCategory").select_option(CATEGORY_ID)
    page.locator(".video-file-input").set_input_files(str(test_mp4))
    page.locator(".video-context-input").fill("Primary browser test video")
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and "/api/v1/admin/signs/" in response.url
        and response.url.endswith("/videos")
    ) as upload_video:
        with page.expect_response(
            lambda response: response.url.endswith("/api/v1/admin/signs")
            and response.request.method == "POST"
        ) as create_sign:
            page.locator("#signFormSubmit").click()
    assert create_sign.value.status == 201
    assert upload_video.value.status == 201

    sign_row = page.locator("#signsTableBody tr", has_text=SIGN_WORD)
    expect(sign_row).to_be_visible()
    sign_row.get_by_role("button", name="Редактировать").click()
    expect(page.locator("#editSignModal")).to_be_visible()
    expect(page.locator("#videosTableBody")).to_contain_text(
        "Primary browser test video"
    )

    page.locator("#editSignWord").fill(UPDATED_SIGN_WORD)
    with page.expect_response(
        lambda response: "/api/v1/admin/signs/" in response.url
        and response.request.method == "PUT"
    ) as update_sign:
        page.locator("#editSignForm button[type='submit']").click()
    assert update_sign.value.status == 200

    updated_row = page.locator("#signsTableBody tr", has_text=UPDATED_SIGN_WORD)
    expect(updated_row).to_be_visible()
    updated_row.get_by_role("button", name="Редактировать").click()
    page.locator("#signDeleteButton").click()
    page.locator("#deleteSignConfirmInput").fill(UPDATED_SIGN_WORD)
    expect(page.locator("#confirmDeleteSignButton")).to_be_enabled()
    with page.expect_response(
        lambda response: "/api/v1/admin/signs/" in response.url
        and response.request.method == "DELETE"
    ) as delete_sign:
        page.locator("#confirmDeleteSignButton").click()
    assert delete_sign.value.status == 200
    expect(page.locator("#signsTableBody")).not_to_contain_text(UPDATED_SIGN_WORD)

    page.goto(f"{live_server}/admin/categories")
    category_row = page.locator("#categoriesTableBody tr", has_text=CATEGORY_NAME)
    category_row.get_by_role("button", name="Редактировать").click()
    page.locator("#categoryDeleteButton").click()
    page.locator("#deleteCategoryConfirmInput").fill(CATEGORY_NAME)
    expect(page.locator("#confirmDeleteCategoryButton")).to_be_enabled()
    with page.expect_response(
        lambda response: response.url.endswith(
            f"/api/v1/admin/categories/{CATEGORY_ID}"
        )
        and response.request.method == "DELETE"
    ) as delete_category:
        page.locator("#confirmDeleteCategoryButton").click()
    assert delete_category.value.status == 200
    expect(page.locator("#categoriesTableBody")).not_to_contain_text(CATEGORY_NAME)
