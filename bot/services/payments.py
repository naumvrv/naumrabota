"""Сервис платежей ЮKassa"""

import uuid
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.database import crud


# Типы платежей
class PaymentType:
    WORKER_SUBSCRIPTION = "worker_subscription"
    EMPLOYER_SUBSCRIPTION = "employer_subscription"
    VACANCY_PUBLICATION = "vacancy_publication"
    VACANCY_BOOST = "vacancy_boost"
    VACANCY_PIN_1D = "vacancy_pin_1d"
    VACANCY_PIN_3D = "vacancy_pin_3d"
    VACANCY_PIN_7D = "vacancy_pin_7d"


def get_payment_amount(payment_type: str) -> int:
    """Получение суммы платежа по типу"""
    amounts = {
        PaymentType.WORKER_SUBSCRIPTION: config.prices.worker_subscription,
        PaymentType.EMPLOYER_SUBSCRIPTION: config.prices.worker_subscription,  # Та же цена
        PaymentType.VACANCY_PUBLICATION: config.prices.vacancy_publication,
        PaymentType.VACANCY_BOOST: config.prices.vacancy_boost,
        PaymentType.VACANCY_PIN_1D: config.prices.vacancy_pin_1d,
        PaymentType.VACANCY_PIN_3D: config.prices.vacancy_pin_3d,
        PaymentType.VACANCY_PIN_7D: config.prices.vacancy_pin_7d,
    }
    return amounts.get(payment_type, 0)


def get_payment_description(payment_type: str) -> str:
    """Получение описания платежа"""
    descriptions = {
        PaymentType.WORKER_SUBSCRIPTION: "Подписка работника на 30 дней",
        PaymentType.EMPLOYER_SUBSCRIPTION: "Подписка работодателя на 30 дней",
        PaymentType.VACANCY_PUBLICATION: "Публикация вакансии",
        PaymentType.VACANCY_BOOST: "Поднятие вакансии",
        PaymentType.VACANCY_PIN_1D: "Закрепление вакансии на 1 день",
        PaymentType.VACANCY_PIN_3D: "Закрепление вакансии на 3 дня",
        PaymentType.VACANCY_PIN_7D: "Закрепление вакансии на 7 дней",
    }
    return descriptions.get(payment_type, "Оплата услуги")


def generate_payment_payload(
    payment_type: str,
    user_id: int,
    vacancy_id: Optional[int] = None
) -> str:
    """Генерация уникального payload для платежа"""
    unique_id = uuid.uuid4().hex[:8]
    if vacancy_id:
        return f"{payment_type}:{user_id}:{vacancy_id}:{unique_id}"
    return f"{payment_type}:{user_id}:{unique_id}"


def parse_payment_payload(payload: str) -> dict:
    """Парсинг payload платежа"""
    parts = payload.split(":")
    result = {
        "payment_type": parts[0] if len(parts) > 0 else "",
        "user_id": int(parts[1]) if len(parts) > 1 else 0,
    }
    if len(parts) == 4:
        result["vacancy_id"] = int(parts[2])
    return result


async def process_successful_payment(
    session: AsyncSession,
    payment_type: str,
    user_id: int,
    vacancy_id: Optional[int] = None,
    provider_payment_id: Optional[str] = None
) -> bool:
    """
    Обработка успешного платежа.
    Активирует соответствующую услугу.
    
    Returns:
        True если услуга активирована успешно
    """
    amount = get_payment_amount(payment_type)
    
    # Создаем запись о платеже
    payment = await crud.create_payment(
        session=session,
        user_id=user_id,
        payment_type=payment_type,
        amount=amount,
        vacancy_id=vacancy_id,
        provider_payment_id=provider_payment_id
    )
    
    # Подтверждаем платеж
    await crud.confirm_payment(session, payment.id)
    
    # Активируем услугу
    if payment_type == PaymentType.WORKER_SUBSCRIPTION:
        await crud.grant_subscription(session, user_id, days=30)
    
    elif payment_type == PaymentType.VACANCY_PUBLICATION:
        # Вакансия уже создана, ничего дополнительно делать не нужно
        pass
        
    elif payment_type == PaymentType.VACANCY_BOOST:
        if vacancy_id:
            await crud.boost_vacancy(session, vacancy_id)
            
    elif payment_type == PaymentType.VACANCY_PIN_1D:
        if vacancy_id:
            await crud.pin_vacancy(session, vacancy_id, days=1)
            
    elif payment_type == PaymentType.VACANCY_PIN_3D:
        if vacancy_id:
            await crud.pin_vacancy(session, vacancy_id, days=3)
            
    elif payment_type == PaymentType.VACANCY_PIN_7D:
        if vacancy_id:
            await crud.pin_vacancy(session, vacancy_id, days=7)
    
    return True
