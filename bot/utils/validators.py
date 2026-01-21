"""Валидаторы данных"""

from bot.config import config


def validate_age(age_str: str) -> tuple[bool, int | None, str]:
    """
    Валидация возраста.
    
    Returns:
        (is_valid, age, error_message)
    """
    try:
        age = int(age_str.strip())
        if 14 <= age <= 80:
            return True, age, ""
        else:
            return False, None, "Возраст должен быть от 14 до 80 лет"
    except ValueError:
        return False, None, "Введите число"


def validate_resume_length(text: str) -> tuple[bool, str]:
    """
    Валидация длины резюме.
    
    Returns:
        (is_valid, error_message)
    """
    max_length = config.limits.max_resume_length
    if len(text) <= max_length:
        return True, ""
    return False, f"Максимум {max_length} символов. Вы ввели: {len(text)}"


def validate_description_length(text: str) -> tuple[bool, str]:
    """
    Валидация длины описания вакансии.
    
    Returns:
        (is_valid, error_message)
    """
    max_length = config.limits.max_description_length
    if len(text) <= max_length:
        return True, ""
    return False, f"Максимум {max_length} символов. Вы ввели: {len(text)}"


def validate_not_empty(text: str) -> tuple[bool, str]:
    """
    Проверка на пустой текст.
    
    Returns:
        (is_valid, error_message)
    """
    if text and text.strip():
        return True, ""
    return False, "Текст не может быть пустым"
