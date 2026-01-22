"""CRUD операции с базой данных"""

from datetime import datetime, date, timedelta
from typing import Optional, Sequence
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User, Vacancy, Payment, AdminLog
from bot.config import config


# ============== USERS ==============

async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Получение пользователя по telegram_id"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int) -> User:
    """Создание нового пользователя"""
    user = User(telegram_id=telegram_id)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> tuple[User, bool]:
    """Получение или создание пользователя. Возвращает (user, is_new)"""
    user = await get_user(session, telegram_id)
    if user:
        return user, False
    user = await create_user(session, telegram_id)
    return user, True


async def update_user(session: AsyncSession, telegram_id: int, **kwargs) -> Optional[User]:
    """Обновление данных пользователя"""
    user = await get_user(session, telegram_id)
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user


async def change_role(session: AsyncSession, telegram_id: int, role: str) -> Optional[User]:
    """Смена роли пользователя"""
    return await update_user(session, telegram_id, role=role, current_index=0)


async def get_all_users(session: AsyncSession, role: Optional[str] = None, limit: Optional[int] = None) -> Sequence[User]:
    """Получение всех пользователей (опционально по роли)"""
    from sqlalchemy.orm import selectinload
    
    query = select(User).order_by(User.created_at.desc())
    
    # Eager load relationships в зависимости от роли
    if role == "employer":
        query = query.options(selectinload(User.vacancies))
    
    if role:
        query = query.where(User.role == role)
    if limit:
        query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def get_users_count(session: AsyncSession, role: Optional[str] = None) -> int:
    """Получение количества пользователей"""
    query = select(func.count(User.telegram_id))
    if role:
        query = query.where(User.role == role)
    result = await session.execute(query)
    return result.scalar() or 0


async def get_active_subscriptions_count(session: AsyncSession) -> int:
    """Получение количества активных подписок"""
    result = await session.execute(
        select(func.count(User.telegram_id)).where(
            User.subscription_until > datetime.utcnow()
        )
    )
    return result.scalar() or 0


# ============== VACANCIES ==============

async def create_vacancy(session: AsyncSession, employer_id: int, **kwargs) -> Vacancy:
    """Создание новой вакансии"""
    vacancy = Vacancy(employer_id=employer_id, **kwargs)
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


async def get_vacancy(session: AsyncSession, vacancy_id: int) -> Optional[Vacancy]:
    """Получение вакансии по ID"""
    result = await session.execute(
        select(Vacancy).where(Vacancy.id == vacancy_id)
    )
    return result.scalar_one_or_none()


async def get_employer_vacancies(session: AsyncSession, employer_id: int) -> Sequence[Vacancy]:
    """Получение всех вакансий работодателя"""
    result = await session.execute(
        select(Vacancy)
        .where(Vacancy.employer_id == employer_id)
        .order_by(Vacancy.created_at.desc())
    )
    return result.scalars().all()


async def get_active_vacancies(session: AsyncSession) -> Sequence[Vacancy]:
    """Получение всех активных вакансий"""
    result = await session.execute(
        select(Vacancy)
        .where(Vacancy.is_active == True)
        .order_by(
            Vacancy.is_pinned.desc(),
            Vacancy.pinned_until.desc().nullslast(),
            Vacancy.is_boosted.desc(),
            Vacancy.created_at.desc()
        )
    )
    return result.scalars().all()


async def update_vacancy(session: AsyncSession, vacancy_id: int, **kwargs) -> Optional[Vacancy]:
    """Обновление вакансии"""
    vacancy = await get_vacancy(session, vacancy_id)
    if not vacancy:
        return None
    
    for key, value in kwargs.items():
        if hasattr(vacancy, key):
            setattr(vacancy, key, value)
    
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


async def delete_vacancy(session: AsyncSession, vacancy_id: int) -> bool:
    """Мягкое удаление вакансии (деактивация)"""
    vacancy = await get_vacancy(session, vacancy_id)
    if not vacancy:
        return False
    
    vacancy.is_active = False
    await session.commit()
    return True


async def boost_vacancy(session: AsyncSession, vacancy_id: int) -> Optional[Vacancy]:
    """Поднятие вакансии"""
    return await update_vacancy(session, vacancy_id, is_boosted=True)


async def pin_vacancy(session: AsyncSession, vacancy_id: int, days: int) -> Optional[Vacancy]:
    """Закрепление вакансии на указанное количество дней"""
    pinned_until = datetime.utcnow() + timedelta(days=days)
    return await update_vacancy(
        session, vacancy_id,
        is_pinned=True,
        pinned_until=pinned_until
    )


async def increment_vacancy_views(session: AsyncSession, vacancy_id: int) -> None:
    """Увеличение счетчика просмотров вакансии"""
    vacancy = await get_vacancy(session, vacancy_id)
    if vacancy:
        vacancy.views_count += 1
        await session.commit()


async def increment_vacancy_responses(session: AsyncSession, vacancy_id: int) -> None:
    """Увеличение счетчика откликов на вакансию"""
    vacancy = await get_vacancy(session, vacancy_id)
    if vacancy:
        vacancy.responses_count += 1
        await session.commit()


async def reset_vacancy_boost(session: AsyncSession, vacancy_id: int) -> None:
    """Сброс поднятия вакансии после показа"""
    await update_vacancy(session, vacancy_id, is_boosted=False)


async def get_vacancies_count(session: AsyncSession, active_only: bool = False) -> int:
    """Получение количества вакансий"""
    query = select(func.count(Vacancy.id))
    if active_only:
        query = query.where(Vacancy.is_active == True)
    result = await session.execute(query)
    return result.scalar() or 0


async def deactivate_expired_vacancies(session: AsyncSession) -> int:
    """Деактивация просроченных вакансий (старше 30 дней)"""
    expiry_date = datetime.utcnow() - timedelta(days=config.limits.vacancy_lifetime_days)
    result = await session.execute(
        select(Vacancy).where(
            and_(
                Vacancy.is_active == True,
                Vacancy.created_at < expiry_date
            )
        )
    )
    vacancies = result.scalars().all()
    count = 0
    for vacancy in vacancies:
        vacancy.is_active = False
        count += 1
    await session.commit()
    return count


async def reset_expired_pins(session: AsyncSession) -> int:
    """Сброс истекших закреплений"""
    result = await session.execute(
        select(Vacancy).where(
            and_(
                Vacancy.is_pinned == True,
                Vacancy.pinned_until < datetime.utcnow()
            )
        )
    )
    vacancies = result.scalars().all()
    count = 0
    for vacancy in vacancies:
        vacancy.is_pinned = False
        vacancy.pinned_until = None
        count += 1
    await session.commit()
    return count


# ============== PAYMENTS ==============

async def create_payment(
    session: AsyncSession,
    user_id: int,
    payment_type: str,
    amount: int,
    vacancy_id: Optional[int] = None,
    provider_payment_id: Optional[str] = None,
    yookassa_id: Optional[str] = None
) -> Payment:
    """Создание записи о платеже"""
    payment = Payment(
        user_id=user_id,
        vacancy_id=vacancy_id,
        payment_type=payment_type,
        amount=amount,
        provider_payment_id=provider_payment_id,
        yookassa_id=yookassa_id,
        status="pending"
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def confirm_payment(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Подтверждение платежа (устаревший метод, используйте mark_payment_succeeded)"""
    return await mark_payment_succeeded(session, payment_id)


async def mark_payment_succeeded(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Отметить платеж как успешный"""
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if payment:
        payment.status = "succeeded"
        await session.commit()
        await session.refresh(payment)
    return payment


async def mark_payment_canceled(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Отметить платеж как отмененный"""
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if payment:
        payment.status = "canceled"
        await session.commit()
        await session.refresh(payment)
    return payment


async def get_payment_by_provider_id(session: AsyncSession, provider_payment_id: str) -> Optional[Payment]:
    """Получение платежа по ID провайдера"""
    result = await session.execute(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    )
    return result.scalar_one_or_none()


async def get_payment_by_yookassa_id(session: AsyncSession, yookassa_id: str) -> Optional[Payment]:
    """Получение платежа по ID ЮKassa"""
    result = await session.execute(
        select(Payment).where(Payment.yookassa_id == yookassa_id)
    )
    return result.scalar_one_or_none()


async def get_payments_sum(
    session: AsyncSession,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> int:
    """Получение суммы платежей за период"""
    query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == "succeeded"
    )
    if from_date:
        query = query.where(Payment.created_at >= from_date)
    if to_date:
        query = query.where(Payment.created_at <= to_date)
    result = await session.execute(query)
    return result.scalar() or 0


async def get_all_payments(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Sequence[Payment]:
    """Получение списка платежей"""
    result = await session.execute(
        select(Payment)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ============== LIMITS ==============

async def check_and_update_daily_views(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """
    Проверка и обновление дневного лимита просмотров.
    Возвращает (can_view, remaining_views)
    """
    user = await get_user(session, user_id)
    if not user:
        return False, 0
    
    # Если есть подписка - безлимит
    if user.has_active_subscription():
        return True, -1  # -1 означает безлимит
    
    today = date.today()
    
    # Сброс счетчика если новый день
    if user.last_view_date != today:
        user.daily_views = 0
        user.last_view_date = today
    
    # Проверка лимита
    limit = config.limits.daily_vacancy_views
    if user.daily_views >= limit:
        return False, 0
    
    # Увеличение счетчика
    user.daily_views += 1
    await session.commit()
    
    return True, limit - user.daily_views


async def check_vacancy_limit(session: AsyncSession, user_id: int) -> tuple[bool, int]:
    """
    Проверка лимита вакансий работодателя.
    Возвращает (has_free, remaining_free)
    """
    user = await get_user(session, user_id)
    if not user:
        return False, 0
    
    # Работодатели не имеют подписки - только бесплатные вакансии
    today = date.today()
    first_of_month = today.replace(day=1)
    
    # Сброс лимита если новый месяц
    if user.vacancies_reset_date is None or user.vacancies_reset_date < first_of_month:
        user.free_vacancies_left = config.limits.free_vacancies_per_month
        user.vacancies_reset_date = first_of_month
        await session.commit()
    
    return user.free_vacancies_left > 0, user.free_vacancies_left


async def grant_free_vacancies(session: AsyncSession, user_id: int, count: int) -> Optional[User]:
    """Выдача бесплатных вакансий работодателю"""
    user = await get_user(session, user_id)
    if not user:
        return None
    
    user.free_vacancies_left += count
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_payments(session: AsyncSession, user_id: int) -> Sequence[Payment]:
    """Получение всех платежей пользователя"""
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )
    return result.scalars().all()


async def decrement_free_vacancies(session: AsyncSession, user_id: int) -> None:
    """Уменьшение счетчика бесплатных вакансий"""
    user = await get_user(session, user_id)
    if user and user.free_vacancies_left > 0:
        user.free_vacancies_left -= 1
        await session.commit()


# ============== SUBSCRIPTIONS ==============

async def grant_subscription(session: AsyncSession, user_id: int, days: int) -> Optional[User]:
    """Выдача подписки пользователю"""
    user = await get_user(session, user_id)
    if not user:
        return None
    
    now = datetime.utcnow()
    if user.subscription_until and user.subscription_until > now:
        # Продление существующей подписки
        user.subscription_until = user.subscription_until + timedelta(days=days)
    else:
        # Новая подписка
        user.subscription_until = now + timedelta(days=days)
    
    await session.commit()
    await session.refresh(user)
    return user


async def cancel_subscription(session: AsyncSession, user_id: int) -> Optional[User]:
    """Отмена подписки пользователя"""
    return await update_user(session, user_id, subscription_until=None)


# ============== ADMIN ==============

async def log_admin_action(
    session: AsyncSession,
    admin_id: int,
    action: str,
    details: Optional[str] = None
) -> AdminLog:
    """Логирование действия администратора"""
    log = AdminLog(admin_id=admin_id, action=action, details=details)
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_admin_logs(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Sequence[AdminLog]:
    """Получение логов администратора"""
    result = await session.execute(
        select(AdminLog)
        .order_by(AdminLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def block_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Блокировка пользователя"""
    return await update_user(session, user_id, is_blocked=True)


async def unblock_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Разблокировка пользователя"""
    return await update_user(session, user_id, is_blocked=False)


async def get_today_responses_count(session: AsyncSession) -> int:
    """Получение количества откликов за сегодня"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(Vacancy.responses_count), 0)).where(
            Vacancy.created_at >= today_start
        )
    )
    return result.scalar() or 0
