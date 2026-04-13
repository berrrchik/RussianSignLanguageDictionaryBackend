"""Unit tests for SBERTSearchService and singleton access."""
from __future__ import annotations

import builtins
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

from app.database import db
from app.models.category import Category
from app.models.sign import Sign
from app.services import sbert_search_service as service_module
from app.services.sbert_search_service import (
    SBERTSearchService,
    get_sbert_search_service,
)


class FakeEmbeddings(list):
    """List-like embeddings object with shape attribute."""

    @property
    def shape(self):
        return (len(self), len(self[0]) if self else 0)


class FakeModel:
    """Minimal fake SentenceTransformer model."""

    def __init__(self, query_embedding=None, embeddings=None):
        self.query_embedding = query_embedding or [0.25, 0.5, 0.75]
        self.embeddings = embeddings or FakeEmbeddings([[0.1, 0.2], [0.3, 0.4]])
        self.encode_calls = []

    def encode(self, payload, **kwargs):
        self.encode_calls.append((payload, kwargs))
        if isinstance(payload, list):
            return self.embeddings
        return self.query_embedding


def _make_service(model_path="test-model", device="cpu"):
    service = SBERTSearchService.__new__(SBERTSearchService)
    service.model_path = model_path
    service.device = device
    return service


def test_detect_device_prefers_cuda(monkeypatch):
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True),
        backends=SimpleNamespace(
            mps=SimpleNamespace(is_available=lambda: False),
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    service = _make_service()

    assert service._detect_device() == "cuda"


def test_detect_device_prefers_mps_when_cuda_unavailable(monkeypatch):
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: False),
        backends=SimpleNamespace(
            mps=SimpleNamespace(is_available=lambda: True),
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    service = _make_service()

    assert service._detect_device() == "mps"


def test_detect_device_falls_back_to_cpu_when_torch_missing(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "torch":
            raise ImportError("torch missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    service = _make_service()

    assert service._detect_device() == "cpu"


def test_model_property_loads_lazily_and_is_cached(monkeypatch):
    model_factory = mock.Mock(return_value=FakeModel())
    monkeypatch.setattr(service_module, "SentenceTransformer", model_factory)

    service = _make_service(model_path="demo-model", device="cpu")

    model_first = service.model
    model_second = service.model

    assert model_first is model_second
    assert model_factory.call_count == 1
    assert model_factory.call_args.kwargs == {"device": "cpu"}
    assert model_factory.call_args.args == ("demo-model",)


def test_words_and_sign_ids_are_loaded_once_and_cached(app_ctx):
    category = Category(id="cat_1", name="Категория", order=1)
    db.session.add(category)
    db.session.add_all(
        [
            Sign(id="sign_b", word="банан", category_id="cat_1"),
            Sign(id="sign_a", word="арбуз", category_id="cat_1"),
        ]
    )
    db.session.commit()

    service = _make_service()

    with mock.patch.object(db.session, "query", wraps=db.session.query) as query_spy:
        words_first = service.words
        words_second = service.words
        sign_ids_first = service.sign_ids
        sign_ids_second = service.sign_ids

    assert words_first == words_second == ["арбуз", "банан"]
    assert sign_ids_first == sign_ids_second == ["sign_a", "sign_b"]
    assert query_spy.call_count == 2


def test_embeddings_are_computed_once_and_cached(monkeypatch):
    fake_model = FakeModel(embeddings=FakeEmbeddings([[0.1, 0.2], [0.3, 0.4]]))
    monkeypatch.setattr(service_module, "sbert_util", SimpleNamespace(cos_sim=mock.Mock()))

    service = _make_service()
    service.__dict__["model"] = fake_model
    service.__dict__["words"] = ["арбуз", "банан"]

    embeddings_first = service.embeddings
    embeddings_second = service.embeddings

    assert embeddings_first is embeddings_second
    assert fake_model.encode_calls == [
        (
            ["арбуз", "банан"],
            {
                "normalize_embeddings": True,
                "show_progress_bar": True,
                "batch_size": 32,
            },
        )
    ]


def test_search_sorts_results_by_similarity_descending(monkeypatch):
    fake_model = FakeModel(query_embedding=[1.0, 0.0])
    monkeypatch.setattr(
        service_module,
        "sbert_util",
        SimpleNamespace(cos_sim=lambda query, embeddings: [[0.2, 0.95, 0.6]]),
    )

    service = _make_service()
    service.__dict__["model"] = fake_model
    service.__dict__["embeddings"] = FakeEmbeddings([[1], [2], [3]])
    service.__dict__["words"] = ["низкий", "высокий", "средний"]
    service.__dict__["sign_ids"] = ["sign_low", "sign_high", "sign_mid"]

    results = service.search("запрос")

    assert results == [
        ("sign_high", "высокий", 0.95),
        ("sign_mid", "средний", 0.6),
        ("sign_low", "низкий", 0.2),
    ]


def test_search_respects_limit(monkeypatch):
    fake_model = FakeModel(query_embedding=[1.0, 0.0])
    monkeypatch.setattr(
        service_module,
        "sbert_util",
        SimpleNamespace(cos_sim=lambda query, embeddings: [[0.2, 0.95, 0.6]]),
    )

    service = _make_service()
    service.__dict__["model"] = fake_model
    service.__dict__["embeddings"] = FakeEmbeddings([[1], [2], [3]])
    service.__dict__["words"] = ["низкий", "высокий", "средний"]
    service.__dict__["sign_ids"] = ["sign_low", "sign_high", "sign_mid"]

    results = service.search("запрос", limit=2)

    assert results == [
        ("sign_high", "высокий", 0.95),
        ("sign_mid", "средний", 0.6),
    ]


def test_search_respects_min_similarity(monkeypatch):
    fake_model = FakeModel(query_embedding=[1.0, 0.0])
    monkeypatch.setattr(
        service_module,
        "sbert_util",
        SimpleNamespace(cos_sim=lambda query, embeddings: [[0.2, 0.95, 0.6]]),
    )

    service = _make_service()
    service.__dict__["model"] = fake_model
    service.__dict__["embeddings"] = FakeEmbeddings([[1], [2], [3]])
    service.__dict__["words"] = ["низкий", "высокий", "средний"]
    service.__dict__["sign_ids"] = ["sign_low", "sign_high", "sign_mid"]

    results = service.search("запрос", min_similarity=0.7)

    assert results == [("sign_high", "высокий", 0.95)]


def test_search_returns_empty_list_for_blank_query():
    service = _make_service()

    assert service.search("") == []
    assert service.search("   ") == []


def test_search_returns_empty_list_when_model_load_fails():
    service = _make_service()

    def broken_model(_self):
        raise RuntimeError("model failed")

    with mock.patch.object(SBERTSearchService, "model", new=property(broken_model)):
        assert service.search("запрос") == []


def test_search_returns_empty_list_when_embeddings_fail(monkeypatch):
    fake_model = FakeModel(query_embedding=[1.0, 0.0])
    monkeypatch.setattr(
        service_module,
        "sbert_util",
        SimpleNamespace(cos_sim=lambda query, embeddings: [[0.2, 0.95, 0.6]]),
    )
    service = _make_service()
    service.__dict__["model"] = fake_model
    service.__dict__["words"] = ["низкий", "высокий", "средний"]
    service.__dict__["sign_ids"] = ["sign_low", "sign_high", "sign_mid"]

    def broken_embeddings(_self):
        raise RuntimeError("embeddings failed")

    with mock.patch.object(SBERTSearchService, "embeddings", new=property(broken_embeddings)):
        assert service.search("запрос") == []


def test_invalidate_cache_clears_cached_properties():
    service = _make_service()
    service.__dict__.update(
        {
            "model": object(),
            "words": ["арбуз"],
            "sign_ids": ["sign_a"],
            "embeddings": FakeEmbeddings([[0.1, 0.2]]),
        }
    )

    service.invalidate_cache()

    assert "model" not in service.__dict__
    assert "words" not in service.__dict__
    assert "sign_ids" not in service.__dict__
    assert "embeddings" not in service.__dict__


def test_get_sbert_search_service_starts_clean_between_tests():
    assert service_module._sbert_search_service is None


def test_get_sbert_search_service_returns_singleton(monkeypatch):
    created = []

    def fake_constructor(*args, **kwargs):
        instance = SimpleNamespace(args=args, kwargs=kwargs, marker=len(created))
        created.append(instance)
        return instance

    monkeypatch.setattr(service_module, "SBERTSearchService", fake_constructor)

    first = get_sbert_search_service(model_path="model-a", device="cpu")
    second = get_sbert_search_service(model_path="model-b", device="cuda")

    assert first is second
    assert len(created) == 1
    assert first.kwargs == {"model_path": "model-a", "device": "cpu"}


def test_get_sbert_search_service_force_reload_creates_new_instance(monkeypatch):
    created = []

    def fake_constructor(*args, **kwargs):
        instance = SimpleNamespace(args=args, kwargs=kwargs, marker=len(created))
        created.append(instance)
        return instance

    monkeypatch.setattr(service_module, "SBERTSearchService", fake_constructor)

    first = get_sbert_search_service(model_path="model-a", device="cpu")
    second = get_sbert_search_service(
        model_path="model-b",
        device="cuda",
        force_reload=True,
    )

    assert first is not second
    assert len(created) == 2
    assert second.kwargs == {"model_path": "model-b", "device": "cuda"}
