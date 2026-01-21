"""Хендлеры платежей через Telegram Payments (ЮKassa)"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    ContentType,
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.keyboards.worker import get_worker_menu
from bot.keyboards.employer import get_employer_menu, get_vacancy_management_keyboard
from bot.utils import texts
from bot.services.payments import (
    PaymentType,
    get_payment_amount,
    get_payment_description,
    generate_payment_payload,
    parse_payment_payload,
    process_successful_payment,
)
from bot.config import config

router = Router(name="payments")

# Провайдер токен для ЮKassa - используется PROVIDER_TOKEN из .env
# Для тестирования используйте токен из @BotFather -> Payments -> Test


def get_provider_token() -> str:
    """Получение токена провайдера"""
    # В продакшене используйте реальный токен из ЮKassa
    # Для тестов можно использовать тестовый токен от BotFather
    import os
    return os.getenv("PAYMENT_PROVIDER_TOKEN", "")


# ============== Покупка подписки работника ==============

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(callback: CallbackQuery, bot: Bot):
    """Покупка подписки работника"""
    await callback.answer()
    
    user_id = callback.from_user.id
    amount = get_payment_amount(PaymentType.WORKER_SUBSCRIPTION)
    description = get_payment_description(PaymentType.WORKER_SUBSCRIPTION)
    payload = generate_payment_payload(PaymentType.WORKER_SUBSCRIPTION, user_id)
    
    provider_token = get_provider_token()
    
    if not provider_token:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )
        return
    
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title="Подписка на 30 дней",
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label="Подписка", amount=amount * 100)],  # В копейках
            start_parameter="subscription",
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )




# ============== Оплата публикации вакансии ==============

@router.callback_query(F.data == "pay_vacancy_publication")
async def pay_vacancy_publication(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Оплата публикации вакансии сверх лимита"""
    await callback.answer()
    
    user_id = callback.from_user.id
    amount = get_payment_amount(PaymentType.VACANCY_PUBLICATION)
    description = get_payment_description(PaymentType.VACANCY_PUBLICATION)
    payload = generate_payment_payload(PaymentType.VACANCY_PUBLICATION, user_id)
    
    provider_token = get_provider_token()
    
    if not provider_token:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )
        return
    
    # Сохраняем что после оплаты нужно создать вакансию
    await state.update_data(pending_vacancy_payment=True)
    
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title="Публикация вакансии",
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label="Публикация вакансии", amount=amount * 100)],
            start_parameter="vacancy_publication",
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )


# ============== Поднятие вакансии ==============

@router.callback_query(F.data.startswith("pay_boost:"))
async def pay_boost_vacancy(callback: CallbackQuery, bot: Bot):
    """Оплата поднятия вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    await callback.answer()
    
    user_id = callback.from_user.id
    amount = get_payment_amount(PaymentType.VACANCY_BOOST)
    description = get_payment_description(PaymentType.VACANCY_BOOST)
    payload = generate_payment_payload(PaymentType.VACANCY_BOOST, user_id, vacancy_id)
    
    provider_token = get_provider_token()
    
    if not provider_token:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )
        return
    
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title="Поднятие вакансии",
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label="Поднятие вакансии", amount=amount * 100)],
            start_parameter="vacancy_boost",
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )


# ============== Закрепление вакансии ==============

@router.callback_query(F.data.startswith("pin_duration:"))
async def pay_pin_vacancy(callback: CallbackQuery, bot: Bot):
    """Оплата закрепления вакансии"""
    parts = callback.data.split(":")
    vacancy_id = int(parts[1])
    days = int(parts[2])
    
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Определяем тип платежа по дням
    payment_type = {
        1: PaymentType.VACANCY_PIN_1D,
        3: PaymentType.VACANCY_PIN_3D,
        7: PaymentType.VACANCY_PIN_7D,
    }.get(days, PaymentType.VACANCY_PIN_1D)
    
    amount = get_payment_amount(payment_type)
    description = get_payment_description(payment_type)
    payload = generate_payment_payload(payment_type, user_id, vacancy_id)
    
    provider_token = get_provider_token()
    
    if not provider_token:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )
        return
    
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=f"Закрепление на {days} дн.",
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label=f"Закрепление на {days} дн.", amount=amount * 100)],
            start_parameter="vacancy_pin",
        )
    except Exception as e:
        await callback.message.answer(
            "❌ Извините, оплата временно не работает. Обратитесь к администратору."
        )


# ============== Pre-checkout query ==============

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, session: AsyncSession):
    """Обработка pre_checkout_query - валидация перед оплатой"""
    # Проверяем что пользователь не заблокирован
    user = await crud.get_user(session, pre_checkout_query.from_user.id)
    
    if user and user.is_blocked:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Ваш аккаунт заблокирован"
        )
        return
    
    # Парсим payload для проверки
    payload_data = parse_payment_payload(pre_checkout_query.invoice_payload)
    payment_type = payload_data.get("payment_type", "")
    
    # Проверка для вакансий - что вакансия существует
    if "vacancy" in payment_type and payment_type != PaymentType.VACANCY_PUBLICATION:
        vacancy_id = payload_data.get("vacancy_id")
        if vacancy_id:
            vacancy = await crud.get_vacancy(session, vacancy_id)
            if not vacancy:
                await pre_checkout_query.answer(
                    ok=False,
                    error_message="Вакансия не найдена"
                )
                return
    
    # Всё в порядке
    await pre_checkout_query.answer(ok=True)


# ============== Successful payment ==============

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment_handler(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    payload_data = parse_payment_payload(payment.invoice_payload)
    
    payment_type = payload_data.get("payment_type", "")
    user_id = payload_data.get("user_id", message.from_user.id)
    vacancy_id = payload_data.get("vacancy_id")
    
    # Обрабатываем платеж
    await process_successful_payment(
        session=session,
        payment_type=payment_type,
        user_id=user_id,
        vacancy_id=vacancy_id,
        provider_payment_id=payment.telegram_payment_charge_id,
    )
    
    description = get_payment_description(payment_type)
    
    # Отправляем подтверждение
    await message.answer(
        texts.PAYMENT_SUCCESS.format(description=description)
    )
    
    # Действия после оплаты в зависимости от типа
    if payment_type == PaymentType.WORKER_SUBSCRIPTION:
        await message.answer(
            texts.WORKER_MENU,
            reply_markup=get_worker_menu()
        )
        
    elif payment_type == PaymentType.VACANCY_PUBLICATION:
        # После оплаты публикации вакансии - начинаем создание
        from bot.states.employer_states import EmployerStates
        await state.update_data(is_paid=True)
        await message.answer(texts.EMPLOYER_VACANCY_START)
        await state.set_state(EmployerStates.waiting_for_title)
        
    elif payment_type in [PaymentType.VACANCY_BOOST, PaymentType.VACANCY_PIN_1D, 
                          PaymentType.VACANCY_PIN_3D, PaymentType.VACANCY_PIN_7D]:
        if vacancy_id:
            vacancy = await crud.get_vacancy(session, vacancy_id)
            if vacancy:
                await message.answer(
                    f"✅ Услуга активирована для вакансии «{vacancy.title}»",
                    reply_markup=get_vacancy_management_keyboard(vacancy_id, vacancy.is_active)
                )
            else:
                await message.answer(
                    texts.EMPLOYER_MENU,
                    reply_markup=get_employer_menu()
                )
        else:
            await message.answer(
                texts.EMPLOYER_MENU,
                reply_markup=get_employer_menu()
            )
