"""Unit tests for Russian sorting helpers."""
from __future__ import annotations

from types import SimpleNamespace

from app.utils.sorting import russian_sort_key, sort_signs_russian


def test_russian_sort_key_sorts_cyrillic_in_expected_order():
    words = ["яблоко", "арбуз", "банан"]

    assert sorted(words, key=russian_sort_key) == ["арбуз", "банан", "яблоко"]


def test_russian_sort_key_handles_yo_with_separate_logic():
    words = ["еж", "ёж", "жук"]

    assert sorted(words, key=russian_sort_key) == ["еж", "ёж", "жук"]


def test_russian_sort_key_places_latin_after_cyrillic():
    words = ["apple", "арбуз", "банан"]

    assert sorted(words, key=russian_sort_key) == ["арбуз", "банан", "apple"]


def test_russian_sort_key_places_non_letters_last():
    words = ["арбуз", "#хеш", "banana"]

    assert sorted(words, key=russian_sort_key) == ["арбуз", "banana", "#хеш"]


def test_russian_sort_key_prioritizes_single_letter_words_within_letter_group():
    words = ["арбуз", "а", "абрикос"]

    assert sorted(words, key=russian_sort_key) == ["а", "абрикос", "арбуз"]


def test_sort_signs_russian_supports_custom_word_getter():
    signs = [
        SimpleNamespace(title="ёж"),
        SimpleNamespace(title="еда"),
        SimpleNamespace(title="apple"),
    ]

    sorted_signs = sort_signs_russian(signs, word_getter=lambda item: item.title)

    assert [item.title for item in sorted_signs] == ["еда", "ёж", "apple"]
