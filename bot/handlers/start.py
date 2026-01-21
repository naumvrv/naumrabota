"""Хендлер стартовой логики и выбора роли"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.keyboards.common import get_role_selection_keyboard
from bot.keyboards.worker import get_worker_menu
from bot.keyboards.employer import get_employer_menu
from bot.utils import texts
from bot.states.worker_states import WorkerStates

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка команды /start"""
    # Очистка состояния
    await state.clear()
    
    user_id = message.from_user.id
    user, is_new = await crud.get_or_create_user(session, user_id)
    
    # Проверка блокировки
    if user.is_blocked:
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return
    
    if is_new or not user.role:
        # Новый пользователь - выбор роли
        await message.answer(
            texts.WELCOME_MESSAGE,
            reply_markup=get_role_selection_keyboard()
        )
    else:
        # Существующий пользователь - перенаправление в меню
        await show_menu_by_role(message, user.role, state)


async def show_menu_by_role(message: Message, role: str, state: FSMContext):
    """Показ меню в зависимости от роли"""
    await state.clear()
    
    if role == "worker":
        await message.answer(
            texts.WORKER_MENU,
            reply_markup=get_worker_menu()
        )
    else:
        await message.answer(
            texts.EMPLOYER_MENU,
            reply_markup=get_employer_menu()
        )


@router.callback_query(F.data.startswith("role:"))
async def process_role_selection(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка выбора роли"""
    role = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    await crud.update_user(session, user_id, role=role)
    
    await callback.answer()
    
    if role == "worker":
        # Работник должен заполнить резюме
        user = await crud.get_user(session, user_id)
        if user and not user.is_resume_complete():
            await callback.message.edit_text(texts.WORKER_RESUME_START)
            await state.set_state(WorkerStates.waiting_for_name)
        else:
            await callback.message.edit_text(
                texts.WORKER_MENU,
                reply_markup=get_worker_menu()
            )
    else:
        # Работодатель сразу попадает в меню
        await callback.message.edit_text(
            texts.EMPLOYER_MENU,
            reply_markup=get_employer_menu()
        )


@router.callback_query(F.data == "change_role")
async def process_change_role(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка смены роли"""
    await state.clear()
    await callback.answer()
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_WORKER, callback_data="role:worker")],
        [InlineKeyboardButton(text=texts.BTN_EMPLOYER, callback_data="role:employer")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="menu")],
    ])
    
    await callback.message.edit_text(
        "🔄 Выберите новую роль:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "menu")
async def process_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Возврат в меню"""
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer()
    
    if user and user.role:
        if user.role == "worker":
            await callback.message.edit_text(
                texts.WORKER_MENU,
                reply_markup=get_worker_menu()
            )
        else:
            await callback.message.edit_text(
                texts.EMPLOYER_MENU,
                reply_markup=get_employer_menu()
            )
    else:
        await callback.message.edit_text(
            texts.WELCOME_MESSAGE,
            reply_markup=get_role_selection_keyboard()
        )


@router.callback_query(F.data == "oferta")
async def process_oferta(callback: CallbackQuery, session: AsyncSession):
    """Показ оферты"""
    await callback.answer()
    from bot.config import config
    from bot.keyboards.common import get_menu_keyboard
    
    user = await crud.get_user(session, callback.from_user.id)
    
    await callback.message.answer(
        texts.OFERTA_MESSAGE.format(email=config.admin.support_email),
        reply_markup=get_menu_keyboard()
    )


@router.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery, session: AsyncSession):
    """Показ контактов поддержки"""
    await callback.answer()
    from bot.config import config
    from bot.keyboards.common import get_menu_keyboard
    
    await callback.message.answer(
        texts.SUPPORT_MESSAGE.format(email=config.admin.support_email),
        reply_markup=get_menu_keyboard()
    )


@router.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка отмены"""
    await state.clear()
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer("Действие отменено")
    
    if user and user.role == "worker":
        await callback.message.edit_text(
            texts.WORKER_MENU,
            reply_markup=get_worker_menu()
        )
    elif user and user.role == "employer":
        await callback.message.edit_text(
            texts.EMPLOYER_MENU,
            reply_markup=get_employer_menu()
        )
    else:
        await callback.message.edit_text(
            texts.WELCOME_MESSAGE,
            reply_markup=get_role_selection_keyboard()
        )
