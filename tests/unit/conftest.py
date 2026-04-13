"""Unit-layer fixtures."""
import pytest


@pytest.fixture(autouse=True)
def _reset_sbert_search_service(reset_sbert_singleton):
    """Не даёт singleton SBERT протекать между unit-тестами."""
    yield
