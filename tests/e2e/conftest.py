"""Browser E2E fixtures backed by the isolated SQLite test application."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server


@pytest.fixture
def live_server(app_sqlite) -> Iterator[str]:
    """Serve the test application for a real browser on an ephemeral port."""
    server = make_server("127.0.0.1", 0, app_sqlite, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def e2e_admin(admin_user) -> dict[str, str]:
    """Return credentials inserted into the temporary test database."""
    return {"username": admin_user.username, "password": "testpass"}


@pytest.fixture
def test_mp4(tmp_path: Path) -> Path:
    """Provide an isolated video payload for browser upload coverage."""
    file_path = tmp_path / "browser-test.mp4"
    file_path.write_bytes(b"browser e2e video bytes")
    return file_path
