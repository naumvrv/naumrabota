"""Сервис проверки лимитов"""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud


async def check_daily_view_limit(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """
    Проверка дневного лимита просмотров вакансий.
    
    Returns:
        (can_view, remaining_views) - -1 означает безлимит при подписке
    """
    return await crud.check_and_update_daily_views(session, user_id)


async def check_vacancy_limit(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """
    Проверка лимита бесплатных вакансий работодателя.
    
    Returns:
        (has_free, remaining_free)
    """
    return await crud.check_vacancy_limit(session, user_id)
