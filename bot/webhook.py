"""Webhook сервер для обработки уведомлений от ЮKassa"""

import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from yookassa import Configuration
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.database.connection import async_session_maker
from bot.database import crud
from bot.services.payments import PaymentType
from bot.keyboards.worker import get_worker_menu
from bot.keyboards.employer import get_employer_menu, get_vacancy_management_keyboard
from bot.utils import texts

app = FastAPI()
logger = logging.getLogger(__name__)

# Инициализация ЮKassa
Configuration.account_id = config.payment.shop_id
Configuration.secret_key = config.payment.secret_key

# Глобальный экземпляр бота (будет установлен при запуске)
bot_instance: Bot = None


def set_bot_instance(bot: Bot):
    """Установка экземпляра бота для отправки уведомлений"""
    global bot_instance
    bot_instance = bot


async def send_notification(telegram_id: int, message: str, reply_markup=None):
    """Отправка уведомления пользователю"""
    global bot_instance
    try:
        # Если bot_instance не установлен, создаем новый
        if not bot_instance:
            if not config.bot.token:
                logger.error("BOT_TOKEN not set, cannot send notification")
                return
            bot_instance = Bot(
                token=config.bot.token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        
        await bot_instance.send_message(
            chat_id=telegram_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending notification to {telegram_id}: {e}")


@app.post(config.payment.webhook_path)
async def yookassa_webhook(request: Request):
    """Обработка webhook от ЮKassa"""
    try:
        event = await request.json()
        event_type = event.get('event')
        payment_obj = event.get('object', {})
        
        logger.info(f"Received webhook event: {event_type}, payment_id: {payment_obj.get('id')}")
        
        if event_type == 'payment.succeeded':
            await handle_payment_succeeded(payment_obj)
        elif event_type == 'payment.canceled':
            await handle_payment_canceled(payment_obj)
        
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_payment_succeeded(payment_obj: dict):
    """Обработка успешного платежа"""
    yookassa_id = payment_obj.get('id')
    metadata = payment_obj.get('metadata', {})
    telegram_id = int(metadata.get('telegram_id', 0))
    amount = float(payment_obj.get('amount', {}).get('value', 0))
    
    if not telegram_id:
        logger.error(f"No telegram_id in metadata for payment {yookassa_id}")
        return
    
    async with async_session_maker() as session:
        try:
            # Проверка уникальности
            existing_payment = await crud.get_payment_by_yookassa_id(session, yookassa_id)
            if existing_payment and existing_payment.status == 'succeeded':
                logger.warning(f"Duplicate webhook for payment {yookassa_id}")
                return
            
            # Получение платежа из БД
            if not existing_payment:
                # Создаем запись если не найдена (на случай если webhook пришел раньше)
                payment = await crud.create_payment(
                    session=session,
                    user_id=telegram_id,
                    payment_type=metadata.get('payment_type', ''),
                    amount=int(amount),
                    vacancy_id=int(metadata.get('vacancy_id')) if metadata.get('vacancy_id') else None,
                    yookassa_id=yookassa_id
                )
            else:
                payment = existing_payment
            
            # Проверка статуса
            if payment.status == 'succeeded':
                logger.info(f"Payment {yookassa_id} already processed")
                return
            
            # Обновление статуса
            await crud.mark_payment_succeeded(session, payment.id)
            
            # Активация услуги
            payment_type = payment.payment_type
            
            if payment_type == PaymentType.WORKER_SUBSCRIPTION:
                await crud.grant_subscription(session, telegram_id, days=30)
                await send_notification(
                    telegram_id,
                    "✅ Подписка активирована на 30 дней!\n\nТеперь у вас безлимитный просмотр вакансий.",
                    reply_markup=get_worker_menu()
                )
                
            elif payment_type == PaymentType.VACANCY_PUBLICATION:
                # Увеличиваем счетчик вакансий работодателя
                await crud.grant_free_vacancies(session, telegram_id, count=1)
                await send_notification(
                    telegram_id,
                    "✅ Оплата прошла успешно!\n\nТеперь вы можете создать вакансию.",
                    reply_markup=get_employer_menu()
                )
                
            elif payment_type == PaymentType.VACANCY_BOOST:
                if payment.vacancy_id:
                    await crud.boost_vacancy(session, payment.vacancy_id)
                    vacancy = await crud.get_vacancy(session, payment.vacancy_id)
                    if vacancy:
                        await send_notification(
                            telegram_id,
                            f"✅ Вакансия «{vacancy.title}» поднята в начало списка!",
                            reply_markup=get_vacancy_management_keyboard(payment.vacancy_id, vacancy.is_active)
                        )
                
            elif payment_type in [PaymentType.VACANCY_PIN_1D, PaymentType.VACANCY_PIN_3D, PaymentType.VACANCY_PIN_7D]:
                if payment.vacancy_id:
                    days = {
                        PaymentType.VACANCY_PIN_1D: 1,
                        PaymentType.VACANCY_PIN_3D: 3,
                        PaymentType.VACANCY_PIN_7D: 7,
                    }.get(payment_type, 1)
                    await crud.pin_vacancy(session, payment.vacancy_id, days=days)
                    vacancy = await crud.get_vacancy(session, payment.vacancy_id)
                    if vacancy:
                        await send_notification(
                            telegram_id,
                            f"✅ Вакансия «{vacancy.title}» закреплена на {days} дн.!",
                            reply_markup=get_vacancy_management_keyboard(payment.vacancy_id, vacancy.is_active)
                        )
            
            await session.commit()
            logger.info(f"Payment {yookassa_id} processed successfully")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error processing payment {yookassa_id}: {e}", exc_info=True)
            raise


async def handle_payment_canceled(payment_obj: dict):
    """Обработка отмененного платежа"""
    yookassa_id = payment_obj.get('id')
    metadata = payment_obj.get('metadata', {})
    telegram_id = int(metadata.get('telegram_id', 0))
    
    async with async_session_maker() as session:
        try:
            payment = await crud.get_payment_by_yookassa_id(session, yookassa_id)
            if payment:
                await crud.mark_payment_canceled(session, payment.id)
                await session.commit()
                logger.info(f"Payment {yookassa_id} marked as canceled")
        except Exception as e:
            logger.error(f"Error processing canceled payment {yookassa_id}: {e}", exc_info=True)


@app.get("/yookassa/return")
async def payment_return(payment_id: str = None):
    """Обработка возврата пользователя после оплаты"""
    return {
        "status": "checking",
        "message": "Проверяем статус платежа. Если оплата прошла успешно, вы получите уведомление в боте."
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    return {"status": "ok"}
