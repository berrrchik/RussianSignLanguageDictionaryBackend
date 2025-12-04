"""
Утилиты для сортировки данных.
"""
from typing import Callable, List, TypeVar

T = TypeVar('T')


def russian_sort_key(sign: T, word_getter: Callable[[T], str] = None) -> tuple:
    """
    Функция для сортировки жестов по русскому алфавиту.
    
    Args:
        sign: Объект жеста (или любой объект с атрибутом word)
        word_getter: Функция для получения слова из объекта (опционально)
        
    Returns:
        Tuple для сортировки: (lang_priority, group_char, length_priority, word_lower_sorted)
    """
    if word_getter:
        word = word_getter(sign)
    else:
        word = sign.word if hasattr(sign, 'word') else str(sign)
    
    word = word.strip()
    if not word:
        return (2, '', 2, '')
    
    original_first = word[0].lower() if word else ''
    word_lower = word.lower()
    word_lower_sorted = word_lower.replace('ё', 'е' + chr(0xFFFF)).replace('Ё', 'Е' + chr(0xFFFF))
    
    if not original_first.isalpha():
        return (2, '', 2, word_lower_sorted)
    
    char_code = ord(original_first)
    is_cyrillic = 0x0400 <= char_code <= 0x04FF
    lang_priority = 0 if is_cyrillic else 1
    
    if original_first == 'ё':
        group_char = 'е' + chr(0xFFFE)
    else:
        group_char = original_first
    
    is_single_letter = len(word.strip()) == 1
    length_priority = 0 if is_single_letter else 1
    
    return (lang_priority, group_char, length_priority, word_lower_sorted)


def sort_signs_russian(signs: List[T], word_getter: Callable[[T], str] = None) -> List[T]:
    """
    Сортировка списка жестов по русскому алфавиту.
    
    Args:
        signs: Список жестов для сортировки
        word_getter: Функция для получения слова из объекта (опционально)
        
    Returns:
        Отсортированный список жестов
    """
    return sorted(signs, key=lambda s: russian_sort_key(s, word_getter))

