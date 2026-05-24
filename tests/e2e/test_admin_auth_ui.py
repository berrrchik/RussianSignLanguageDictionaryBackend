"""Browser coverage for the administrator authentication flow."""

from playwright.sync_api import Page, expect


def test_admin_login_redirects_to_dashboard_and_stores_token(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
) -> None:
    page.goto(f"{live_server}/admin/login")
    page.locator("#username").fill(e2e_admin["username"])
    page.locator("#password").fill(e2e_admin["password"])

    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/admin/auth/login")
        and response.request.method == "POST"
    ) as response_info:
        page.get_by_role("button", name="Войти").click()

    assert response_info.value.status == 200
    page.wait_for_url(f"{live_server}/admin/dashboard")
    expect(
        page.get_by_role("heading", name="Добро пожаловать в административную панель")
    ).to_be_visible()
    assert page.evaluate("window.localStorage.getItem('authToken')") is not None


def test_admin_login_displays_invalid_credentials(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
) -> None:
    page.goto(f"{live_server}/admin/login")
    page.locator("#username").fill(e2e_admin["username"])
    page.locator("#password").fill("wrong-password")

    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/admin/auth/login")
        and response.request.method == "POST"
    ) as response_info:
        page.get_by_role("button", name="Войти").click()

    assert response_info.value.status == 401
    expect(page.locator("#errorMessage")).to_be_visible()
    expect(page.locator("#errorMessage")).to_contain_text(
        "Неверный username или password"
    )
    assert page.url == f"{live_server}/admin/login"
    assert page.evaluate("window.localStorage.getItem('authToken')") is None


def test_admin_page_without_token_redirects_to_login(
    page: Page,
    live_server: str,
) -> None:
    page.goto(f"{live_server}/admin/signs")

    page.wait_for_url(f"{live_server}/admin/login")
    assert page.evaluate("window.localStorage.getItem('authToken')") is None


def test_invalid_token_is_cleared_after_api_unauthorized(
    page: Page,
    live_server: str,
) -> None:
    page.goto(f"{live_server}/admin/login")
    page.evaluate("window.localStorage.setItem('authToken', 'invalid-token')")

    page.goto(f"{live_server}/admin/signs")
    page.wait_for_url(f"{live_server}/admin/login")

    assert page.evaluate("window.localStorage.getItem('authToken')") is None
