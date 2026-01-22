"""Общие клавиатуры"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from bot.utils import texts
from bot.config import config


def get_role_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора роли"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_WORKER, callback_data="role:worker")],
        [InlineKeyboardButton(text=texts.BTN_EMPLOYER, callback_data="role:employer")],
    ])


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отправки геолокации (старая версия, для обратной совместимости)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_SEND_LOCATION, request_location=True)],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_location_method_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора способа указания местоположения"""
    web_app_url = config.geocoding.web_app_url
    
    keyboard = []
    
    # Кнопка отправки текущего местоположения
    keyboard.append([KeyboardButton(text=texts.BTN_SEND_LOCATION, request_location=True)])
    
    # Кнопка выбора на карте (Web App)
    if web_app_url:
        keyboard.append([KeyboardButton(
            text=texts.BTN_SELECT_ON_MAP,
            web_app=WebAppInfo(url=web_app_url)
        )])
    
    # Кнопка ввода адреса
    keyboard.append([KeyboardButton(text=texts.BTN_ENTER_ADDRESS)])
    
    # Кнопка отмены
    keyboard.append([KeyboardButton(text="❌ Отмена")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")],
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back")],
    ])


def get_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата в меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_MENU, callback_data="menu")],
    ])


def get_oferta_support_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с офертой и поддержкой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BTN_OFERTA, callback_data="oferta"),
            InlineKeyboardButton(text=texts.BTN_SUPPORT, callback_data="support"),
        ],
    ])
