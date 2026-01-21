"""Сервис статистики для админ-панели"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud


@dataclass
class BotStatistics:
    """Статистика бота"""
    total_users: int
    workers: int
    employers: int
    active_vacancies: int
    total_vacancies: int
    active_subscriptions: int
    today_payments: int
    week_payments: int
    month_payments: int
    today_responses: int


async def get_bot_statistics(session: AsyncSession) -> BotStatistics:
    """Получение полной статистики бота"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    return BotStatistics(
        total_users=await crud.get_users_count(session),
        workers=await crud.get_users_count(session, role="worker"),
        employers=await crud.get_users_count(session, role="employer"),
        active_vacancies=await crud.get_vacancies_count(session, active_only=True),
        total_vacancies=await crud.get_vacancies_count(session),
        active_subscriptions=await crud.get_active_subscriptions_count(session),
        today_payments=await crud.get_payments_sum(session, from_date=today_start),
        week_payments=await crud.get_payments_sum(session, from_date=week_ago),
        month_payments=await crud.get_payments_sum(session, from_date=month_ago),
        today_responses=await crud.get_today_responses_count(session),
    )
