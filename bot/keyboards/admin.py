"""Клавиатуры для админ-панели"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils import texts


def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_ADMIN_STATS, callback_data="admin:stats")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_USERS, callback_data="admin:users")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_VACANCIES, callback_data="admin:vacancies")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_SUBSCRIPTIONS, callback_data="admin:subscriptions")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_PAYMENTS, callback_data="admin:payments")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_BROADCAST, callback_data="admin:broadcast")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_LOGS, callback_data="admin:logs")],
        [InlineKeyboardButton(text=texts.BTN_ADMIN_EXIT, callback_data="admin:exit")],
    ])


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="admin:menu")],
    ])


def get_user_management_keyboard(user_id: int, is_blocked: bool, user_role: str = None) -> InlineKeyboardMarkup:
    """Клавиатура управления пользователем"""
    buttons = []
    
    if user_role == "employer":
        # Для работодателей: выдача бесплатных вакансий
        buttons.append([InlineKeyboardButton(text="📋 Выдать бесплатные вакансии", callback_data=f"admin:grant_vacancies:{user_id}")])
    else:
        # Для работников: выдача подписки
        buttons.append([InlineKeyboardButton(text="💳 Выдать подписку", callback_data=f"admin:grant_sub:{user_id}")])
        buttons.append([InlineKeyboardButton(text="❌ Отменить подписку", callback_data=f"admin:cancel_sub:{user_id}")])
    
    if is_blocked:
        buttons.append([InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin:unblock:{user_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin:block:{user_id}")])
    
    buttons.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data="admin:users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления пользователями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по ID", callback_data="admin:search_user")],
        [InlineKeyboardButton(text="📋 Список работников", callback_data="admin:list_workers")],
        [InlineKeyboardButton(text="📋 Список работодателей", callback_data="admin:list_employers")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="admin:menu")],
    ])


def get_subscription_management_keyboard() -> InlineKeyboardMarkup:
    """Меню управления подписками"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin:grant_subscription")],
        [InlineKeyboardButton(text="📋 Выдать бесплатные вакансии", callback_data="admin:grant_vacancies_menu")],
        [InlineKeyboardButton(text="📋 Активные подписки", callback_data="admin:active_subs")],
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="admin:menu")],
    ])


def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Выбор получателей рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="broadcast:all")],
        [InlineKeyboardButton(text="👤 Только работникам", callback_data="broadcast:workers")],
        [InlineKeyboardButton(text="🧑‍💼 Только работодателям", callback_data="broadcast:employers")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="admin:menu")],
    ])


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:confirm")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="admin:menu")],
    ])


def get_vacancy_admin_keyboard(vacancy_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура администрирования вакансии"""
    buttons = []
    
    if is_active:
        buttons.append([InlineKeyboardButton(text="🚫 Деактивировать", callback_data=f"admin:deactivate_vac:{vacancy_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Активировать", callback_data=f"admin:activate_vac:{vacancy_id}")])
    
    buttons.append([InlineKeyboardButton(text="🗑 Удалить полностью", callback_data=f"admin:delete_vac:{vacancy_id}")])
    buttons.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data="admin:vacancies")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
