"""Integration tests for the semantic search API endpoint."""
from __future__ import annotations

from app.constants import MAX_DESCRIPTION_LENGTH


class FakeSearchService:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.calls = []

    def search(self, search_query, limit, min_similarity):
        self.calls.append(
            {
                "search_query": search_query,
                "limit": limit,
                "min_similarity": min_similarity,
            }
        )
        if self.error is not None:
            raise self.error
        return self.results


def test_search_sbert_returns_formatted_success_payload(client, monkeypatch):
    fake_service = FakeSearchService(
        results=[
            ("sign-1", "привет", 0.91234),
            ("sign-2", "пока", 0.70111),
        ]
    )
    captured = {}

    def fake_get_service(model_path):
        captured["model_path"] = model_path
        return fake_service

    monkeypatch.setattr("app.routes.search.get_sbert_search_service", fake_get_service)

    response = client.post(
        "/api/v1/search/sbert",
        json={"text": "привет", "limit": 2, "min_similarity": 0.3},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"] == {
        "query": "привет",
        "results": [
            {"id": "sign-1", "word": "привет", "similarity": 0.9123},
            {"id": "sign-2", "word": "пока", "similarity": 0.7011},
        ],
        "total_found": 2,
        "model": "ai-forever/sbert_large_nlu_ru",
    }
    assert captured["model_path"] == "ai-forever/sbert_large_nlu_ru"
    assert fake_service.calls == [
        {"search_query": "привет", "limit": 2, "min_similarity": 0.3}
    ]


def test_search_sbert_rejects_blank_text(client):
    response = client.post("/api/v1/search/sbert", json={"text": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "VALIDATION_ERROR",
        "message": "Поле text не может быть пустым",
    }


def test_search_sbert_rejects_too_long_text(client):
    response = client.post(
        "/api/v1/search/sbert",
        json={"text": "а" * (MAX_DESCRIPTION_LENGTH + 1)},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == {
        "code": "VALIDATION_ERROR",
        "message": f"Текст не может быть длиннее {MAX_DESCRIPTION_LENGTH} символов",
    }


def test_search_sbert_resets_invalid_limit_and_min_similarity_to_defaults(client, monkeypatch):
    fake_service = FakeSearchService(results=[("sign-1", "привет", 0.8)])

    monkeypatch.setattr(
        "app.routes.search.get_sbert_search_service",
        lambda model_path: fake_service,
    )

    response = client.post(
        "/api/v1/search/sbert",
        json={"text": "привет", "limit": "oops", "min_similarity": 9},
    )

    assert response.status_code == 200
    assert fake_service.calls == [
        {"search_query": "привет", "limit": 10, "min_similarity": 0.0}
    ]


def test_search_sbert_replaces_swagger_placeholder_model_path(client, monkeypatch):
    fake_service = FakeSearchService(results=[])
    captured = {}

    def fake_get_service(model_path):
        captured["model_path"] = model_path
        return fake_service

    monkeypatch.setattr("app.routes.search.get_sbert_search_service", fake_get_service)

    response = client.post(
        "/api/v1/search/sbert",
        json={"text": "привет", "model_path": "string"},
    )

    assert response.status_code == 200
    assert captured["model_path"] == "ai-forever/sbert_large_nlu_ru"
    assert response.get_json()["data"]["model"] == "ai-forever/sbert_large_nlu_ru"


def test_search_sbert_returns_500_when_service_raises(client, monkeypatch):
    fake_service = FakeSearchService(error=RuntimeError("model exploded"))

    monkeypatch.setattr(
        "app.routes.search.get_sbert_search_service",
        lambda model_path: fake_service,
    )

    response = client.post("/api/v1/search/sbert", json={"text": "привет"})

    assert response.status_code == 500
    assert response.get_json()["error"] == {
        "code": "SEARCH_ERROR",
        "message": "Ошибка поиска: model exploded",
    }


def test_search_sbert_returns_success_with_empty_results(client, monkeypatch):
    fake_service = FakeSearchService(results=[])

    monkeypatch.setattr(
        "app.routes.search.get_sbert_search_service",
        lambda model_path: fake_service,
    )

    response = client.post("/api/v1/search/sbert", json={"text": "редкий запрос"})

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {
            "query": "редкий запрос",
            "results": [],
            "total_found": 0,
            "model": "ai-forever/sbert_large_nlu_ru",
        },
    }

