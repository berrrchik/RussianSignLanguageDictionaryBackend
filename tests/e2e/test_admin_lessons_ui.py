"""Browser coverage for administrator lesson and lesson-video management."""

from pathlib import Path

from playwright.sync_api import Page, expect


LESSON_TITLE = "Browser Lesson"
UPDATED_LESSON_TITLE = "Updated Browser Lesson"


def _login(page: Page, live_server: str, e2e_admin: dict[str, str]) -> None:
    page.goto(f"{live_server}/admin/login")
    page.locator("#username").fill(e2e_admin["username"])
    page.locator("#password").fill(e2e_admin["password"])
    page.get_by_role("button", name="Войти").click()
    page.wait_for_url(f"{live_server}/admin/dashboard")


def test_admin_lesson_form_rejects_create_without_required_video(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
) -> None:
    lesson_create_requests: list[str] = []
    page.on(
        "request",
        lambda request: lesson_create_requests.append(request.url)
        if request.method == "POST"
        and request.url.endswith("/api/v1/admin/lessons")
        else None,
    )

    _login(page, live_server, e2e_admin)
    page.goto(f"{live_server}/admin/lessons")
    page.get_by_role("button", name="Создать урок").click()
    page.locator("#lessonTitle").fill("Lesson Without Video")
    page.locator("#lessonDescription").fill("Browser validation coverage")
    page.locator("#lessonOrder").fill("1")

    page.locator("#lessonFormSubmit").click()

    expect(page.locator("#lessonFormError")).to_be_visible()
    expect(page.locator("#lessonFormError")).to_contain_text(
        "Видео обязательно при создании урока"
    )
    assert lesson_create_requests == []


def test_admin_can_create_update_replace_video_and_delete_lesson(
    page: Page,
    live_server: str,
    e2e_admin: dict[str, str],
    test_mp4: Path,
) -> None:
    _login(page, live_server, e2e_admin)
    page.goto(f"{live_server}/admin/lessons")

    page.get_by_role("button", name="Создать урок").click()
    expect(page.locator("#lessonModal")).to_be_visible()
    page.locator("#lessonTitle").fill(LESSON_TITLE)
    page.locator("#lessonDescription").fill("Lesson created in Playwright e2e")
    page.locator("#lessonOrder").fill("1")
    page.locator("#lessonVideoFile").set_input_files(str(test_mp4))
    expect(page.locator("#lessonVideoUploadButton")).to_be_visible()
    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/admin/lessons")
        and response.request.method == "POST"
    ) as create_lesson:
        with page.expect_response(
            lambda response: "/api/v1/admin/lessons/" in response.url
            and response.url.endswith("/video")
            and response.request.method == "POST"
        ) as upload_video:
            page.locator("#lessonVideoUploadButton").click()
    assert create_lesson.value.status == 201
    assert upload_video.value.status == 200
    expect(page.locator("#lessonVideoPreviewGroup")).to_be_visible()

    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.request.method == "PUT"
    ) as save_lesson:
        page.locator("#lessonFormSubmit").click()
    assert save_lesson.value.status == 200
    lesson_row = page.locator("#lessonsTableBody tr", has_text=LESSON_TITLE)
    expect(lesson_row).to_be_visible()

    lesson_row.get_by_role("button", name="Редактировать").click()
    page.locator("#lessonTitle").fill(UPDATED_LESSON_TITLE)
    page.locator("#lessonDescription").fill("Updated through the lesson modal")
    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.request.method == "PUT"
    ) as update_lesson:
        page.locator("#lessonFormSubmit").click()
    assert update_lesson.value.status == 200

    updated_row = page.locator("#lessonsTableBody tr", has_text=UPDATED_LESSON_TITLE)
    expect(updated_row).to_be_visible()
    updated_row.get_by_role("button", name="Редактировать").click()
    page.locator("#lessonDeleteVideoButton").click()
    page.locator("#deleteVideoConfirmInput").fill(UPDATED_LESSON_TITLE)
    expect(page.locator("#confirmDeleteVideoButton")).to_be_enabled()
    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.url.endswith("/video")
        and response.request.method == "DELETE"
    ) as delete_video:
        page.locator("#confirmDeleteVideoButton").click()
    assert delete_video.value.status == 200
    expect(page.locator("#lessonVideoRequired")).to_be_visible()

    page.locator("#lessonVideoFile").set_input_files(str(test_mp4))
    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.url.endswith("/video")
        and response.request.method == "POST"
    ) as replacement_video:
        page.locator("#lessonVideoUploadButton").click()
    assert replacement_video.value.status == 200
    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.request.method == "PUT"
    ) as save_replacement:
        page.locator("#lessonFormSubmit").click()
    assert save_replacement.value.status == 200

    page.locator("#lessonsTableBody tr", has_text=UPDATED_LESSON_TITLE).get_by_role(
        "button", name="Редактировать"
    ).click()
    page.locator("#lessonDeleteButton").click()
    page.locator("#deleteLessonConfirmInput").fill(UPDATED_LESSON_TITLE)
    expect(page.locator("#confirmDeleteLessonButton")).to_be_enabled()
    with page.expect_response(
        lambda response: "/api/v1/admin/lessons/" in response.url
        and response.request.method == "DELETE"
        and not response.url.endswith("/video")
    ) as delete_lesson:
        page.locator("#confirmDeleteLessonButton").click()
    assert delete_lesson.value.status == 200
    expect(page.locator("#lessonsTableBody")).to_contain_text("Уроки не найдены")
