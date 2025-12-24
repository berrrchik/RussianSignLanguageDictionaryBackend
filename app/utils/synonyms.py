"""
Утилиты для работы с синонимами жестов.
"""
from typing import List, Dict

from app.database import db
from app.models.sign import Sign
from app.models.sign_synonym import SignSynonym


def get_sign_synonyms(sign_id: str) -> List[Dict[str, str]]:
    """
    Получение списка синонимов для жеста.
    
    Args:
        sign_id: ID жеста
        
    Returns:
        Список словарей с id и word синонимов
    """
    synonyms_query = SignSynonym.query.filter(
        (SignSynonym.sign_id_1 == sign_id) | (SignSynonym.sign_id_2 == sign_id)
    ).all()
    
    seen_ids = set()
    synonyms = []
    for synonym in synonyms_query:
        other_sign_id = synonym.sign_id_2 if synonym.sign_id_1 == sign_id else synonym.sign_id_1
        if other_sign_id in seen_ids:
            continue
        seen_ids.add(other_sign_id)
        
        other_sign = Sign.query.get(other_sign_id)
        if other_sign:
            synonyms.append({
                'id': other_sign.id,
                'word': other_sign.word
            })
    
    return synonyms


def delete_synonym_relation(sign_id_1: str, sign_id_2: str) -> bool:
    """
    Удаляет двустороннюю связь синонимов.
    
    Args:
        sign_id_1: ID первого жеста
        sign_id_2: ID второго жеста
        
    Returns:
        True если связь найдена и удалена, False иначе
    """
    synonyms = SignSynonym.query.filter(
        ((SignSynonym.sign_id_1 == sign_id_1) & (SignSynonym.sign_id_2 == sign_id_2)) |
        ((SignSynonym.sign_id_1 == sign_id_2) & (SignSynonym.sign_id_2 == sign_id_1))
    ).all()
    
    if not synonyms:
        return False
    
    for synonym in synonyms:
        db.session.delete(synonym)
    
    return True


def check_synonym_exists(sign_id_1: str, sign_id_2: str) -> bool:
    """
    Проверяет существование связи синонимов.
    
    Args:
        sign_id_1: ID первого жеста
        sign_id_2: ID второго жеста
        
    Returns:
        True если связь существует, False иначе
    """
    existing = SignSynonym.query.filter(
        ((SignSynonym.sign_id_1 == sign_id_1) & (SignSynonym.sign_id_2 == sign_id_2)) |
        ((SignSynonym.sign_id_1 == sign_id_2) & (SignSynonym.sign_id_2 == sign_id_1))
    ).first()
    
    return existing is not None


def create_synonym_relation(sign_id_1: str, sign_id_2: str) -> None:
    """
    Создает двустороннюю связь синонимов.
    
    Args:
        sign_id_1: ID первого жеста
        sign_id_2: ID второго жеста
    """
    synonym1 = SignSynonym(sign_id_1=sign_id_1, sign_id_2=sign_id_2)
    synonym2 = SignSynonym(sign_id_1=sign_id_2, sign_id_2=sign_id_1)
    
    db.session.add(synonym1)
    db.session.add(synonym2)

