"""
Утилиты для генерации ID сущностей.
"""
import re
from app.models.lesson import Lesson


def generate_lesson_id() -> str:
    """
    Генерирует простой ID урока в формате lesson_N.
    
    Находит максимальный номер из существующих ID вида lesson_N
    и возвращает следующий по порядку.
    
    Returns:
        Уникальный ID урока (например, lesson_1, lesson_2)
    """
    # Получить все существующие уроки
    existing_lessons = Lesson.query.all()
    
    if not existing_lessons:
        return 'lesson_1'
    
    # Найти максимальный номер из существующих ID
    max_number = 0
    pattern = re.compile(r'^lesson_(\d+)$')
    
    for lesson in existing_lessons:
        match = pattern.match(lesson.id)
        if match:
            number = int(match.group(1))
            max_number = max(max_number, number)
    
    # Сгенерировать следующий ID
    next_number = max_number + 1
    return f'lesson_{next_number}'
