"""Хендлеры админ-панели"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.keyboards.admin import (
    get_admin_menu,
    get_admin_back_keyboard,
    get_user_management_keyboard,
    get_users_menu_keyboard,
    get_subscription_management_keyboard,
    get_broadcast_target_keyboard,
    get_broadcast_confirm_keyboard,
    get_vacancy_admin_keyboard,
)
from bot.keyboards.worker import get_worker_menu
from bot.keyboards.employer import get_employer_menu
from bot.utils import texts
from bot.services.statistics import get_bot_statistics
from bot.states.employer_states import AdminBroadcastStates, AdminSearchStates, AdminSubscriptionStates
from bot.config import config

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    """Проверка является ли пользователь админом"""
    return user_id == config.admin.admin_id


@router.message(Command("user"))
async def show_user_info(message: Message, session: AsyncSession):
    """Показ информации о пользователе по команде /user ID"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    # Парсим ID из команды
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Использование: /user [Telegram_ID]")
        return
    
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    
    # Получаем пользователя
    user = await crud.get_user(session, user_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {user_id} не найден")
        return
    
    # Формируем информацию
    role_text = "👷 Работник" if user.role == "worker" else "🏢 Работодатель"
    sub_text = "✅ Активна" if user.has_active_subscription() else "❌ Нет"
    
    info_text = f"""👤 <b>Информация о пользователе</b>

🆔 Telegram ID: <code>{user.telegram_id}</code>
👤 Имя: {user.name or 'Не указано'}
📋 Роль: {role_text}
🎂 Возраст: {user.age or 'Не указано'}
🏙 Город: {user.city or 'Не указано'}
💳 Подписка: {sub_text}
📅 Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    if user.role == "worker":
        info_text += f"\n📝 Резюме: {user.resume[:100] if user.resume else 'Не указано'}..."
    elif user.role == "employer":
        # Считаем вакансии
        from sqlalchemy import select, func
        from bot.database.models import Vacancy
        
        result = await session.execute(
            select(func.count(Vacancy.id)).where(Vacancy.employer_id == user.telegram_id)
        )
        vacancies_count = result.scalar() or 0
        
        info_text += f"\n📋 Вакансий создано: {vacancies_count}"
    
    await message.answer(
        info_text,
        reply_markup=get_admin_back_keyboard()
    )


# ============== Вход в админку ==============

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin для входа в админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        texts.ADMIN_MENU,
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "admin:menu")
async def show_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Показ главного меню админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.clear()
    await callback.answer()
    
    # Пытаемся отредактировать сообщение, если не получается - отправляем новое
    try:
        await callback.message.edit_text(
            texts.ADMIN_MENU,
            reply_markup=get_admin_menu()
        )
    except Exception:
        await callback.message.answer(
            texts.ADMIN_MENU,
            reply_markup=get_admin_menu()
        )


@router.callback_query(F.data == "admin:exit")
async def exit_admin(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer("Выход из админ-панели")
    
    if user and user.role == "worker":
        try:
            await callback.message.edit_text(
                texts.WORKER_MENU,
                reply_markup=get_worker_menu()
            )
        except Exception:
            pass
    else:
        try:
            await callback.message.edit_text(
                texts.EMPLOYER_MENU,
                reply_markup=get_employer_menu()
            )
        except Exception:
            pass


# ============== Статистика ==============

@router.callback_query(F.data == "admin:stats")
async def show_statistics(callback: CallbackQuery, session: AsyncSession):
    """Показ статистики бота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    stats = await get_bot_statistics(session)
    
    stats_text = texts.ADMIN_STATISTICS.format(
        total_users=stats.total_users,
        workers=stats.workers,
        employers=stats.employers,
        active_vacancies=stats.active_vacancies,
        total_vacancies=stats.total_vacancies,
        active_subscriptions=stats.active_subscriptions,
        today_payments=stats.today_payments,
        week_payments=stats.week_payments,
        month_payments=stats.month_payments,
        today_responses=stats.today_responses,
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_back_keyboard()
    )


# ============== Управление пользователями ==============

@router.callback_query(F.data == "admin:users")
async def show_users_menu(callback: CallbackQuery):
    """Меню управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "👥 Управление пользователями",
        reply_markup=get_users_menu_keyboard()
    )


@router.callback_query(F.data == "admin:list_workers")
async def show_workers_list(callback: CallbackQuery, session: AsyncSession):
    """Показ списка работников"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    workers = await crud.get_all_users(session, role="worker", limit=50)
    
    if not workers:
        await callback.message.edit_text(
            "👷 Работники\n\nСписок пуст",
            reply_markup=get_admin_back_keyboard()
        )
        return
    
    text = "👷 Список работников (последние 50):\n\n"
    for user in workers:
        sub_status = "✅ Подписка" if user.has_active_subscription() else "❌ Нет подписки"
        text += f"• ID: {user.telegram_id} | {user.name or 'Без имени'} | {sub_status}\n"
    
    text += f"\n💡 Для просмотра пользователя: /user ID"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


@router.callback_query(F.data == "admin:list_employers")
async def show_employers_list(callback: CallbackQuery, session: AsyncSession):
    """Показ списка работодателей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    employers = await crud.get_all_users(session, role="employer", limit=50)
    
    if not employers:
        await callback.message.edit_text(
            "🏢 Работодатели\n\nСписок пуст",
            reply_markup=get_admin_back_keyboard()
        )
        return
    
    text = "🏢 Список работодателей (последние 50):\n\n"
    for user in employers:
        # Теперь vacancies загружены через selectinload, можно безопасно использовать
        vacancies_count = len(user.vacancies) if user.vacancies else 0
        text += f"• ID: {user.telegram_id} | {user.name or 'Без имени'} | Вакансий: {vacancies_count}\n"
    
    text += f"\n💡 Для просмотра пользователя: /user ID"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


@router.callback_query(F.data == "admin:search_user")
async def start_search_user(callback: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text("🔍 Введите Telegram ID пользователя:")
    await state.set_state(AdminSearchStates.waiting_for_user_id)


@router.message(AdminSearchStates.waiting_for_user_id)
async def process_search_user(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка поиска пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный ID (число)")
        return
    
    user = await crud.get_user(session, user_id)
    
    if not user:
        await message.answer(
            texts.ADMIN_USER_NOT_FOUND,
            reply_markup=get_users_menu_keyboard()
        )
        await state.clear()
        return
    
    await state.clear()
    
    # Статус подписки
    if user.has_active_subscription():
        sub_status = f"✅ Активна до {user.subscription_until.strftime('%d.%m.%Y')}"
    else:
        sub_status = "❌ Неактивна"
    
    role_text = "👤 Работник" if user.role == "worker" else "🧑‍💼 Работодатель" if user.role == "employer" else "❓ Не выбрана"
    
    user_info = texts.ADMIN_USER_INFO.format(
        telegram_id=user.telegram_id,
        role=role_text,
        name=user.name or "Не указано",
        city=user.city or "Не указан",
        created=user.created_at.strftime("%d.%m.%Y %H:%M"),
        subscription_status=sub_status,
        daily_views=user.daily_views,
    )
    
    if user.is_blocked:
        user_info += "\n\n🚫 ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН"
    
    await message.answer(
        user_info,
        reply_markup=get_user_management_keyboard(user_id, user.is_blocked, user.role)
    )
    
    # Логируем действие
    await crud.log_admin_action(
        session,
        message.from_user.id,
        "view_user",
        f"Просмотр пользователя {user_id}"
    )


@router.callback_query(F.data.startswith("admin:block:"))
async def block_user(callback: CallbackQuery, session: AsyncSession):
    """Блокировка пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    await crud.block_user(session, user_id)
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "block_user",
        f"Заблокирован пользователь {user_id}"
    )
    
    await callback.answer(texts.ADMIN_USER_BLOCKED.format(user_id=user_id))
    
    # Обновляем кнопки
    user = await crud.get_user(session, user_id)
    if user:
        await callback.message.edit_reply_markup(
            reply_markup=get_user_management_keyboard(user_id, True, user.role)
        )


@router.callback_query(F.data.startswith("admin:unblock:"))
async def unblock_user(callback: CallbackQuery, session: AsyncSession):
    """Разблокировка пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    await crud.unblock_user(session, user_id)
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "unblock_user",
        f"Разблокирован пользователь {user_id}"
    )
    
    await callback.answer(texts.ADMIN_USER_UNBLOCKED.format(user_id=user_id))
    
    user = await crud.get_user(session, user_id)
    if user:
        await callback.message.edit_reply_markup(
            reply_markup=get_user_management_keyboard(user_id, False, user.role)
        )


# ============== Управление подписками ==============

@router.callback_query(F.data == "admin:subscriptions")
async def show_subscriptions_menu(callback: CallbackQuery):
    """Меню управления подписками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "💰 Управление подписками",
        reply_markup=get_subscription_management_keyboard()
    )


@router.callback_query(F.data == "admin:grant_vacancies_menu")
async def start_grant_vacancies_from_menu(callback: CallbackQuery, state: FSMContext):
    """Начало выдачи бесплатных вакансий из меню подписок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "📋 Выдача бесплатных вакансий работодателям\n\nВведите Telegram ID работодателя:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_employer_id)


@router.callback_query(F.data == "admin:active_subs")
async def show_active_subscriptions(callback: CallbackQuery, session: AsyncSession):
    """Показ списка активных подписок"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    from datetime import datetime
    from sqlalchemy import select, and_
    from bot.database.models import User
    
    # Получаем всех пользователей с активными подписками
    now = datetime.utcnow()
    query = select(User).where(
        and_(
            User.subscription_until.isnot(None),
            User.subscription_until > now
        )
    ).order_by(User.subscription_until.desc())
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    if not users:
        await callback.message.edit_text(
            "📋 Активные подписки\n\nСписок пуст",
            reply_markup=get_admin_back_keyboard()
        )
        return
    
    text = f"📋 Активные подписки ({len(users)}):\n\n"
    for user in users:
        role_emoji = "👷" if user.role == "worker" else "🏢"
        days_left = (user.subscription_until - now).days
        text += f"{role_emoji} ID: <code>{user.telegram_id}</code> | {user.name or 'Без имени'}\n"
        text += f"   До: {user.subscription_until.strftime('%d.%m.%Y')} ({days_left} дн.)\n\n"
    
    text += "💡 Для управления: /user [ID]"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


@router.callback_query(F.data == "admin:grant_subscription")
async def start_grant_subscription(callback: CallbackQuery, state: FSMContext):
    """Начало выдачи подписки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "Введите Telegram ID пользователя для выдачи подписки:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_user_id)


@router.message(AdminSubscriptionStates.waiting_for_user_id)
async def process_subscription_user_id(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ID пользователя для подписки"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный ID (число)")
        return
    
    user = await crud.get_user(session, user_id)
    if not user:
        await message.answer(texts.ADMIN_USER_NOT_FOUND)
        await state.clear()
        return
    
    await state.update_data(subscription_user_id=user_id)
    await message.answer(
        "Введите количество дней подписки:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_days)


@router.message(AdminSubscriptionStates.waiting_for_days)
async def process_subscription_days(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка количества дней подписки"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное количество дней (положительное число)")
        return
    
    data = await state.get_data()
    user_id = data.get("subscription_user_id")
    
    await crud.grant_subscription(session, user_id, days)
    
    await crud.log_admin_action(
        session,
        message.from_user.id,
        "grant_subscription",
        f"Выдана подписка пользователю {user_id} на {days} дней"
    )
    
    await state.clear()
    await message.answer(
        f"✅ Подписка выдана пользователю {user_id} на {days} дней",
        reply_markup=get_admin_back_keyboard()
    )


@router.message(AdminSubscriptionStates.waiting_for_employer_id)
async def process_employer_id_for_vacancies(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ID работодателя для выдачи вакансий"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный ID (число)")
        return
    
    user = await crud.get_user(session, user_id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    if user.role != "employer":
        await message.answer("❌ Это не работодатель. Введите ID работодателя.")
        return
    
    await state.update_data(vacancies_user_id=user_id)
    await message.answer(
        f"Работодатель: {user.name or 'Без имени'} (ID: {user_id})\nТекущий баланс: {user.free_vacancies_left} вакансий\n\nВведите количество вакансий для выдачи:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_vacancies_count)


@router.message(AdminSubscriptionStates.waiting_for_vacancies_count)
async def process_grant_vacancies(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка выдачи бесплатных вакансий"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное количество (положительное число)")
        return
    
    data = await state.get_data()
    user_id = data.get("vacancies_user_id")
    
    if not user_id:
        await message.answer("❌ Ошибка: не найден ID работодателя. Начните заново.")
        await state.clear()
        return
    
    user = await crud.grant_free_vacancies(session, user_id, count)
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    await crud.log_admin_action(
        session,
        message.from_user.id,
        "grant_free_vacancies",
        f"Выдано {count} бесплатных вакансий работодателю {user_id}"
    )
    
    await state.clear()
    await message.answer(
        f"✅ Работодателю {user_id} выдано {count} бесплатных вакансий.\n\nТекущий баланс: {user.free_vacancies_left}",
        reply_markup=get_admin_back_keyboard()
    )


@router.callback_query(F.data.startswith("admin:grant_sub:"))
async def quick_grant_subscription(callback: CallbackQuery, state: FSMContext):
    """Быстрая выдача подписки из карточки пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    await callback.answer()
    await state.update_data(subscription_user_id=user_id)
    await callback.message.edit_text(
        f"Введите количество дней подписки для пользователя {user_id}:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_days)


@router.callback_query(F.data.startswith("admin:grant_vacancies:"))
async def start_grant_vacancies(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Начало выдачи бесплатных вакансий работодателю"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    
    # Проверяем что это работодатель
    user = await crud.get_user(session, user_id)
    if not user or user.role != "employer":
        await callback.answer("❌ Это не работодатель", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(vacancies_user_id=user_id)
    await callback.message.edit_text(
        f"Введите количество бесплатных вакансий для работодателя {user_id}:\n\nТекущий баланс: {user.free_vacancies_left}",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminSubscriptionStates.waiting_for_vacancies_count)


@router.callback_query(F.data == "admin:back", AdminSubscriptionStates.waiting_for_user_id)
@router.callback_query(F.data == "admin:back", AdminSubscriptionStates.waiting_for_days)
@router.callback_query(F.data == "admin:back", AdminSubscriptionStates.waiting_for_vacancies_count)
@router.callback_query(F.data == "admin:back", AdminSubscriptionStates.waiting_for_employer_id)
async def cancel_subscription_grant(callback: CallbackQuery, state: FSMContext):
    """Отмена выдачи подписки/вакансий"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text(
        "💰 Управление подписками",
        reply_markup=get_subscription_management_keyboard()
    )


@router.callback_query(F.data.startswith("admin:cancel_sub:"))
async def cancel_subscription(callback: CallbackQuery, session: AsyncSession):
    """Отмена подписки пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[2])
    await crud.cancel_subscription(session, user_id)
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "cancel_subscription",
        f"Отменена подписка пользователя {user_id}"
    )
    
    await callback.answer(texts.ADMIN_SUBSCRIPTION_CANCELLED.format(user_id=user_id))
    
    # Обновляем информацию о пользователе
    user = await crud.get_user(session, user_id)
    if user:
        await callback.message.edit_reply_markup(
            reply_markup=get_user_management_keyboard(user_id, user.is_blocked, user.role)
        )


# ============== Управление вакансиями ==============

@router.callback_query(F.data == "admin:vacancies")
async def show_vacancies_admin(callback: CallbackQuery, session: AsyncSession):
    """Показ вакансий для админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    active_count = await crud.get_vacancies_count(session, active_only=True)
    total_count = await crud.get_vacancies_count(session)
    
    text = f"""💼 Управление вакансиями

📊 Статистика:
• Активных: {active_count}
• Всего: {total_count}

Для управления конкретной вакансией введите её ID через команду:
/vacancy_admin ID"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


@router.message(Command("vacancy_admin"))
async def admin_vacancy_details(message: Message, session: AsyncSession):
    """Просмотр вакансии админом"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        vacancy_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Использование: /vacancy_admin ID")
        return
    
    vacancy = await crud.get_vacancy(session, vacancy_id)
    if not vacancy:
        await message.answer("❌ Вакансия не найдена")
        return
    
    text = f"""📌 Вакансия #{vacancy.id}

Название: {vacancy.title}
Город: {vacancy.city}
Зарплата: {vacancy.salary}
Работодатель ID: {vacancy.employer_id}

👀 Просмотров: {vacancy.views_count}
📨 Откликов: {vacancy.responses_count}

Статус: {"✅ Активна" if vacancy.is_active else "❌ Неактивна"}
Закреплена: {"Да" if vacancy.is_pinned_now() else "Нет"}
Поднята: {"Да" if vacancy.is_boosted else "Нет"}

Создана: {vacancy.created_at.strftime("%d.%m.%Y %H:%M")}"""
    
    await message.answer(
        text,
        reply_markup=get_vacancy_admin_keyboard(vacancy_id, vacancy.is_active)
    )


@router.callback_query(F.data.startswith("admin:deactivate_vac:"))
async def deactivate_vacancy_admin(callback: CallbackQuery, session: AsyncSession):
    """Деактивация вакансии админом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    vacancy_id = int(callback.data.split(":")[2])
    await crud.update_vacancy(session, vacancy_id, is_active=False)
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "deactivate_vacancy",
        f"Деактивирована вакансия {vacancy_id}"
    )
    
    await callback.answer("✅ Вакансия деактивирована")
    await callback.message.edit_reply_markup(
        reply_markup=get_vacancy_admin_keyboard(vacancy_id, False)
    )


@router.callback_query(F.data.startswith("admin:activate_vac:"))
async def activate_vacancy_admin(callback: CallbackQuery, session: AsyncSession):
    """Активация вакансии админом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    vacancy_id = int(callback.data.split(":")[2])
    await crud.update_vacancy(session, vacancy_id, is_active=True)
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "activate_vacancy",
        f"Активирована вакансия {vacancy_id}"
    )
    
    await callback.answer("✅ Вакансия активирована")
    await callback.message.edit_reply_markup(
        reply_markup=get_vacancy_admin_keyboard(vacancy_id, True)
    )


# ============== История платежей ==============

@router.callback_query(F.data == "admin:payments")
async def show_payments_admin(callback: CallbackQuery, session: AsyncSession):
    """Показ истории платежей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    payments = await crud.get_all_payments(session, limit=10)
    
    if not payments:
        text = "📈 История платежей пуста"
    else:
        text = "📈 Последние платежи:\n\n"
        for p in payments:
            status_emoji = "✅" if p.status == "completed" else "⏳" if p.status == "pending" else "↩️"
            text += f"{status_emoji} {p.amount}₽ | {p.payment_type} | User: {p.user_id}\n"
            text += f"   {p.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


# ============== Логи ==============

@router.callback_query(F.data == "admin:logs")
async def show_admin_logs(callback: CallbackQuery, session: AsyncSession):
    """Показ логов действий админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    logs = await crud.get_admin_logs(session, limit=15)
    
    if not logs:
        text = "📋 Логи пусты"
    else:
        text = "📋 Последние действия:\n\n"
        for log in logs:
            text += f"• {log.action}\n"
            text += f"  {log.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if log.details:
                text += f"  {log.details[:50]}...\n" if len(log.details) > 50 else f"  {log.details}\n"
            text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_back_keyboard()
    )


# ============== Рассылка ==============

@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery):
    """Начало рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "📢 Выберите получателей рассылки:",
        reply_markup=get_broadcast_target_keyboard()
    )


@router.callback_query(F.data.startswith("broadcast:"))
async def process_broadcast_target(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора получателей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    target = callback.data.split(":")[1]
    
    if target == "confirm":
        # Подтверждение отправки
        await send_broadcast(callback, state)
        return
    
    await callback.answer()
    await state.update_data(broadcast_target=target)
    await callback.message.edit_text(texts.ADMIN_BROADCAST_START)
    await state.set_state(AdminBroadcastStates.waiting_for_text)


@router.message(AdminBroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка текста рассылки"""
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    
    # Подсчет получателей
    if target == "all":
        recipients = await crud.get_users_count(session)
        target_text = "всем пользователям"
    elif target == "workers":
        recipients = await crud.get_users_count(session, role="worker")
        target_text = "работникам"
    else:
        recipients = await crud.get_users_count(session, role="employer")
        target_text = "работодателям"
    
    await state.update_data(broadcast_text=message.text)
    
    confirm_text = texts.ADMIN_BROADCAST_CONFIRM.format(
        recipients=f"{recipients} ({target_text})",
        text=message.text[:200] + "..." if len(message.text) > 200 else message.text
    )
    
    await message.answer(
        confirm_text,
        reply_markup=get_broadcast_confirm_keyboard()
    )
    await state.set_state(AdminBroadcastStates.waiting_for_confirmation)


async def send_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отправка рассылки"""
    from bot.database.connection import async_session_maker
    
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    text = data.get("broadcast_text", "")
    
    if not text:
        await callback.answer("Ошибка: нет текста рассылки")
        return
    
    await callback.answer("Отправка началась...")
    
    # Создаем новую сессию для рассылки
    async with async_session_maker() as session:
        await _do_broadcast(callback, session, target, text, state)


async def _do_broadcast(callback: CallbackQuery, session: AsyncSession, target: str, text: str, state: FSMContext):
    """Выполнение рассылки"""
    role = None if target == "all" else "worker" if target == "workers" else "employer"
    users = await crud.get_all_users(session, role=role)
    
    sent = 0
    errors = 0
    
    for user in users:
        if user.is_blocked:
            continue
        try:
            await callback.bot.send_message(user.telegram_id, text)
            sent += 1
        except Exception:
            errors += 1
    
    await crud.log_admin_action(
        session,
        callback.from_user.id,
        "broadcast",
        f"Рассылка: {target}, отправлено: {sent}, ошибок: {errors}"
    )
    
    await state.clear()
    
    # Пытаемся отредактировать, если не получается - отправляем новое сообщение
    try:
        await callback.message.edit_text(
            f"✅ Рассылка завершена!\n\n📊 Отправлено: {sent}\n❌ Ошибок: {errors}",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            f"✅ Рассылка завершена!\n\n📊 Отправлено: {sent}\n❌ Ошибок: {errors}",
            reply_markup=get_admin_back_keyboard()
        )
