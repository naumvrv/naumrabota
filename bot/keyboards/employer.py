"""Клавиатуры для работодателя"""

from typing import Sequence
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils import texts
from bot.database.models import Vacancy


def get_employer_menu() -> InlineKeyboardMarkup:
    """Главное меню работодателя"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_CREATE_VACANCY, callback_data="employer:create_vacancy")],
        [InlineKeyboardButton(text=texts.BTN_MY_VACANCIES, callback_data="employer:my_vacancies")],
        [InlineKeyboardButton(text=texts.BTN_PAID_SERVICES, callback_data="employer:paid_services")],
        [InlineKeyboardButton(text=texts.BTN_CHANGE_ROLE, callback_data="change_role")],
        [
            InlineKeyboardButton(text=texts.BTN_OFERTA, callback_data="oferta"),
            InlineKeyboardButton(text=texts.BTN_SUPPORT, callback_data="support"),
        ],
    ])


def get_my_vacancies_keyboard(vacancies: Sequence[Vacancy]) -> InlineKeyboardMarkup:
    """Клавиатура со списком вакансий работодателя"""
    buttons = []
    for vacancy in vacancies:
        status = "✅" if vacancy.is_active else "❌"
        pin = "📌" if vacancy.is_pinned_now() else ""
        boost = "🔝" if vacancy.is_boosted else ""
        # Добавляем ID вакансии в текст
        text = f"{status}{pin}{boost} ID:{vacancy.id} {vacancy.title[:25]}"
        buttons.append([
            InlineKeyboardButton(text=text, callback_data=f"vacancy:{vacancy.id}")
        ])
    
    buttons.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data="employer:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_vacancy_management_keyboard(vacancy_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления вакансией"""
    buttons = []
    
    if is_active:
        buttons.append([InlineKeyboardButton(text=texts.BTN_EDIT, callback_data=f"edit_vacancy:{vacancy_id}")])
        buttons.append([
            InlineKeyboardButton(text=texts.BTN_BOOST, callback_data=f"boost_vacancy:{vacancy_id}"),
            InlineKeyboardButton(text=texts.BTN_PIN, callback_data=f"pin_vacancy:{vacancy_id}"),
        ])
        buttons.append([InlineKeyboardButton(text=texts.BTN_DELETE, callback_data=f"delete_vacancy:{vacancy_id}")])
    
    buttons.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data="employer:my_vacancies")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pin_duration_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора срока закрепления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 день - 100 ₽", callback_data=f"pin_duration:{vacancy_id}:1")],
        [InlineKeyboardButton(text="3 дня - 250 ₽", callback_data=f"pin_duration:{vacancy_id}:3")],
        [InlineKeyboardButton(text="7 дней - 500 ₽", callback_data=f"pin_duration:{vacancy_id}:7")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=f"vacancy:{vacancy_id}")],
    ])


def get_vacancy_limit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при превышении лимита вакансий"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_PAY, callback_data="pay_vacancy_publication")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="employer:menu")],
    ])


def get_vacancy_edit_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования вакансии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Название", callback_data=f"edit_vac:{vacancy_id}:title")],
        [InlineKeyboardButton(text="🏙 Город", callback_data=f"edit_vac:{vacancy_id}:city")],
        [InlineKeyboardButton(text="📍 Геопозиция", callback_data=f"edit_vac:{vacancy_id}:location")],
        [InlineKeyboardButton(text="💰 Зарплата", callback_data=f"edit_vac:{vacancy_id}:salary")],
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_vac:{vacancy_id}:description")],
        [InlineKeyboardButton(text="📷 Фото", callback_data=f"edit_vac:{vacancy_id}:photo")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=f"vacancy:{vacancy_id}")],
    ])


def get_cancel_edit_vacancy_keyboard(vacancy_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены редактирования вакансии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_edit_vacancy:{vacancy_id}")],
    ])


def get_paid_services_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура платных услуг"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои покупки", callback_data="employer:my_payments")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="employer:menu")],
    ])
