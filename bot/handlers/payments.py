"""Хендлеры платежей через ЮKassa"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.utils import texts
from bot.services.payments import (
    PaymentType,
    get_payment_amount,
    create_yookassa_payment,
)

router = Router(name="payments")
logger = logging.getLogger(__name__)


# ============== Покупка подписки работника ==============

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Покупка подписки работника"""
    await callback.answer()
    
    user_id = callback.from_user.id
    amount = get_payment_amount(PaymentType.WORKER_SUBSCRIPTION)
    
    try:
        # Создание платежа через ЮKassa
        payment_data = await create_yookassa_payment(
            payment_type=PaymentType.WORKER_SUBSCRIPTION,
            user_id=user_id,
            amount=amount,
            session=session
        )
        
        # Отправка ссылки пользователю
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="worker:subscription")]
        ])
        
        await callback.message.edit_text(
            "💳 Оплата подписки\n\n"
            "Нажмите на кнопку ниже для оплаты через ЮKassa.\n"
            "После оплаты подписка активируется автоматически.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error creating payment for subscription: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Извините, оплата временно не работает. Обратитесь к администратору.\n\nОшибка: {str(e)}"
        )




# ============== Оплата публикации вакансии ==============

@router.callback_query(F.data == "pay_vacancy_publication")
async def pay_vacancy_publication(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    """Оплата публикации вакансии"""
    await callback.answer()
    
    user_id = callback.from_user.id
    amount = get_payment_amount(PaymentType.VACANCY_PUBLICATION)
    
    try:
        # Создание платежа
        payment_data = await create_yookassa_payment(
            payment_type=PaymentType.VACANCY_PUBLICATION,
            user_id=user_id,
            amount=amount,
            session=session
        )
        
        # Сохраняем payment_id в state для последующей проверки
        await state.update_data(
            pending_payment_id=payment_data['db_payment_id'],
            pending_vacancy_payment=True
        )
        
        # Отправка ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="employer:menu")]
        ])
        
        await callback.message.edit_text(
            "💳 Оплата публикации вакансии\n\n"
            "Стоимость: 100 ₽\n"
            "После оплаты вы сможете создать вакансию.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error creating payment for subscription: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Извините, оплата временно не работает. Обратитесь к администратору.\n\nОшибка: {str(e)}"
        )


# ============== Поднятие вакансии ==============

@router.callback_query(F.data.startswith("pay_boost:"))
async def pay_boost_vacancy(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Оплата поднятия вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Проверка вакансии
    vacancy = await crud.get_vacancy(session, vacancy_id)
    if not vacancy or vacancy.employer_id != user_id:
        await callback.answer("❌ Вакансия не найдена")
        return
    
    amount = get_payment_amount(PaymentType.VACANCY_BOOST)
    
    try:
        # Создание платежа
        payment_data = await create_yookassa_payment(
            payment_type=PaymentType.VACANCY_BOOST,
            user_id=user_id,
            amount=amount,
            vacancy_id=vacancy_id,
            session=session
        )
        
        # Отправка ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"vacancy:{vacancy_id}")]
        ])
        
        # Проверяем, есть ли фото в сообщении
        if callback.message.photo:
            await callback.message.edit_caption(
                caption="💳 Оплата поднятия вакансии\n\n"
                        "Стоимость: 200 ₽\n"
                        "После оплаты вакансия будет поднята в начало списка.",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "💳 Оплата поднятия вакансии\n\n"
                "Стоимость: 200 ₽\n"
                "После оплаты вакансия будет поднята в начало списка.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error creating payment for subscription: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Извините, оплата временно не работает. Обратитесь к администратору.\n\nОшибка: {str(e)}"
        )


# ============== Закрепление вакансии ==============

@router.callback_query(F.data.startswith("pin_duration:"))
async def pay_pin_vacancy(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Оплата закрепления вакансии"""
    parts = callback.data.split(":")
    vacancy_id = int(parts[1])
    days = int(parts[2])
    
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Определение типа платежа
    payment_type = {
        1: PaymentType.VACANCY_PIN_1D,
        3: PaymentType.VACANCY_PIN_3D,
        7: PaymentType.VACANCY_PIN_7D,
    }.get(days)
    
    if not payment_type:
        await callback.answer("❌ Некорректный срок")
        return
    
    # Проверка вакансии
    vacancy = await crud.get_vacancy(session, vacancy_id)
    if not vacancy or vacancy.employer_id != user_id:
        await callback.answer("❌ Вакансия не найдена")
        return
    
    amount = get_payment_amount(payment_type)
    
    try:
        # Создание платежа
        payment_data = await create_yookassa_payment(
            payment_type=payment_type,
            user_id=user_id,
            amount=amount,
            vacancy_id=vacancy_id,
            session=session
        )
        
        # Отправка ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"vacancy:{vacancy_id}")]
        ])
        
        # Проверяем, есть ли фото в сообщении
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=f"💳 Оплата закрепления на {days} дн.\n\n"
                        f"Стоимость: {amount} ₽\n"
                        "После оплаты вакансия будет закреплена.",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                f"💳 Оплата закрепления на {days} дн.\n\n"
                f"Стоимость: {amount} ₽\n"
                "После оплаты вакансия будет закреплена.",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error creating payment for subscription: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Извините, оплата временно не работает. Обратитесь к администратору.\n\nОшибка: {str(e)}"
        )


