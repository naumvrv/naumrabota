"""Клавиатуры для работника"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils import texts


def get_worker_menu() -> InlineKeyboardMarkup:
    """Главное меню работника"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_VIEW_VACANCIES, callback_data="worker:view_vacancies")],
        [InlineKeyboardButton(text=texts.BTN_EDIT_RESUME, callback_data="worker:edit_resume")],
        [InlineKeyboardButton(text=texts.BTN_SUBSCRIPTION, callback_data="worker:subscription")],
        [InlineKeyboardButton(text=texts.BTN_CHANGE_ROLE, callback_data="change_role")],
        [
            InlineKeyboardButton(text=texts.BTN_OFERTA, callback_data="oferta"),
            InlineKeyboardButton(text=texts.BTN_SUPPORT, callback_data="support"),
        ],
    ])


def get_vacancy_buttons(vacancy_id: int) -> InlineKeyboardMarkup:
    """Кнопки под вакансией"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BTN_RESPOND, callback_data=f"respond:{vacancy_id}"),
            InlineKeyboardButton(text=texts.BTN_NEXT, callback_data="next_vacancy"),
        ],
        [InlineKeyboardButton(text=texts.BTN_MENU, callback_data="worker:menu")],
    ])


def get_limit_reached_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при достижении лимита просмотров"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_BUY_SUBSCRIPTION, callback_data="worker:subscription")],
        [InlineKeyboardButton(text=texts.BTN_MENU, callback_data="worker:menu")],
    ])


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура покупки подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_BUY_SUBSCRIPTION, callback_data="buy_subscription")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="worker:menu")],
    ])


def get_start_search_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура начала поиска после создания резюме"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Начать поиск вакансий", callback_data="worker:view_vacancies")],
    ])


def get_resume_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура редактирования резюме"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Имя", callback_data="edit_resume:name")],
        [InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_resume:age")],
        [InlineKeyboardButton(text="🏙 Город", callback_data="edit_resume:city")],
        [InlineKeyboardButton(text="📍 Геопозиция", callback_data="edit_resume:location")],
        [InlineKeyboardButton(text="📝 Резюме", callback_data="edit_resume:resume")],
        [InlineKeyboardButton(text="📷 Фото", callback_data="edit_resume:photo")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="worker:menu")],
    ])


def get_no_vacancies_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура когда вакансий нет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_MENU, callback_data="worker:menu")],
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="worker:cancel_edit")],
    ])
