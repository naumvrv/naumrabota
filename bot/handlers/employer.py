"""Хендлеры для работодателя"""

from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.keyboards.common import get_location_keyboard
from bot.keyboards.employer import (
    get_employer_menu,
    get_my_vacancies_keyboard,
    get_vacancy_management_keyboard,
    get_pin_duration_keyboard,
    get_vacancy_limit_keyboard,
    get_vacancy_edit_keyboard,
    get_paid_services_keyboard,
)
from bot.utils import texts
from bot.utils.validators import validate_description_length, validate_not_empty
from bot.states.employer_states import EmployerStates, EmployerEditStates
from bot.services.limits import check_vacancy_limit
from bot.config import config

router = Router(name="employer")


# ============== Меню работодателя ==============

@router.callback_query(F.data == "employer:menu")
async def show_employer_menu(callback: CallbackQuery, state: FSMContext):
    """Показ меню работодателя"""
    await state.clear()
    await callback.answer()
    
    # Если предыдущее сообщение было с фото, удаляем его и отправляем новое
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            texts.EMPLOYER_MENU,
            reply_markup=get_employer_menu()
        )
    else:
        await callback.message.edit_text(
            texts.EMPLOYER_MENU,
            reply_markup=get_employer_menu()
        )


# ============== FSM: Создание вакансии ==============

@router.callback_query(F.data == "employer:create_vacancy")
async def start_create_vacancy(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Начало создания вакансии"""
    user_id = callback.from_user.id
    
    # Проверка лимита
    has_free, remaining = await check_vacancy_limit(session, user_id)
    
    await callback.answer()
    
    # Если предыдущее сообщение было с фото, удаляем его
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if not has_free:
            await callback.message.answer(
                texts.VACANCY_LIMIT_REACHED,
                reply_markup=get_vacancy_limit_keyboard()
            )
            await state.update_data(need_payment=True)
        else:
            await callback.message.answer(texts.EMPLOYER_VACANCY_START)
            await state.set_state(EmployerStates.waiting_for_title)
    else:
        if not has_free:
            await callback.message.edit_text(
                texts.VACANCY_LIMIT_REACHED,
                reply_markup=get_vacancy_limit_keyboard()
            )
            await state.update_data(need_payment=True)
        else:
            await callback.message.edit_text(texts.EMPLOYER_VACANCY_START)
            await state.set_state(EmployerStates.waiting_for_title)


@router.message(EmployerStates.waiting_for_title)
async def process_vacancy_title(message: Message, state: FSMContext):
    """Обработка названия вакансии"""
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await state.update_data(title=message.text.strip())
    await message.answer(texts.EMPLOYER_VACANCY_CITY)
    await state.set_state(EmployerStates.waiting_for_city)


@router.message(EmployerStates.waiting_for_city)
async def process_vacancy_city(message: Message, state: FSMContext):
    """Обработка города вакансии"""
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await state.update_data(city=message.text.strip())
    await message.answer(
        texts.EMPLOYER_VACANCY_LOCATION,
        reply_markup=get_location_keyboard()
    )
    await state.set_state(EmployerStates.waiting_for_location)


@router.message(EmployerStates.waiting_for_location, F.location)
async def process_vacancy_location(message: Message, state: FSMContext):
    """Обработка геопозиции вакансии"""
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await message.answer(
        texts.EMPLOYER_VACANCY_SALARY,
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(EmployerStates.waiting_for_salary)


@router.message(EmployerStates.waiting_for_location)
async def process_vacancy_location_invalid(message: Message):
    """Некорректная геопозиция"""
    await message.answer(
        texts.ERROR_NOT_LOCATION,
        reply_markup=get_location_keyboard()
    )


@router.message(EmployerStates.waiting_for_salary)
async def process_vacancy_salary(message: Message, state: FSMContext):
    """Обработка зарплаты"""
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await state.update_data(salary=message.text.strip())
    await message.answer(texts.EMPLOYER_VACANCY_DESCRIPTION)
    await state.set_state(EmployerStates.waiting_for_description)


@router.message(EmployerStates.waiting_for_description)
async def process_vacancy_description(message: Message, state: FSMContext):
    """Обработка описания"""
    is_valid, error = validate_description_length(message.text or "")
    if not is_valid:
        await message.answer(
            texts.ERROR_DESCRIPTION_TOO_LONG.format(length=len(message.text or ""))
        )
        return
    
    await state.update_data(description=message.text.strip())
    await message.answer(texts.EMPLOYER_VACANCY_PHOTO)
    await state.set_state(EmployerStates.waiting_for_photo)


@router.message(EmployerStates.waiting_for_photo, F.photo)
async def process_vacancy_photo(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка фото вакансии"""
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    # Создаем вакансию
    vacancy = await crud.create_vacancy(
        session,
        employer_id=message.from_user.id,
        title=data.get("title"),
        city=data.get("city"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        salary=data.get("salary"),
        description=data.get("description"),
        photo_id=photo_id,
    )
    
    # Уменьшаем счетчик бесплатных вакансий
    if not data.get("is_paid"):
        await crud.decrement_free_vacancies(session, message.from_user.id)
    
    await state.clear()
    await message.answer(
        texts.VACANCY_CREATED,
        reply_markup=get_employer_menu()
    )


@router.message(EmployerStates.waiting_for_photo)
async def process_vacancy_photo_invalid(message: Message):
    """Некорректное фото"""
    await message.answer(texts.ERROR_NOT_PHOTO)


# ============== Мои вакансии ==============

@router.callback_query(F.data == "employer:my_vacancies")
async def show_my_vacancies(callback: CallbackQuery, session: AsyncSession):
    """Показ списка вакансий работодателя"""
    vacancies = await crud.get_employer_vacancies(session, callback.from_user.id)
    await callback.answer()
    
    # Если предыдущее сообщение было с фото, удаляем его
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        
        if not vacancies:
            await callback.message.answer(
                texts.MY_VACANCIES_EMPTY,
                reply_markup=get_employer_menu()
            )
        else:
            await callback.message.answer(
                "📄 Ваши вакансии:",
                reply_markup=get_my_vacancies_keyboard(vacancies)
            )
    else:
        if not vacancies:
            await callback.message.edit_text(
                texts.MY_VACANCIES_EMPTY,
                reply_markup=get_employer_menu()
            )
        else:
            await callback.message.edit_text(
                "📄 Ваши вакансии:",
                reply_markup=get_my_vacancies_keyboard(vacancies)
            )


async def show_vacancy_details_helper(bot: Bot, user_id: int, vacancy):
    """Вспомогательная функция для показа вакансии"""
    expires = vacancy.created_at + timedelta(days=config.limits.vacancy_lifetime_days)
    details_text = texts.VACANCY_DETAILS.format(
        title=vacancy.title,
        city=vacancy.city,
        salary=vacancy.salary,
        description=vacancy.description,
        views=vacancy.views_count,
        responses=vacancy.responses_count,
        created=vacancy.created_at.strftime("%d.%m.%Y"),
        expires=expires.strftime("%d.%m.%Y")
    )
    
    if vacancy.photo_id:
        await bot.send_photo(
            chat_id=user_id,
            photo=vacancy.photo_id,
            caption=details_text,
            reply_markup=get_vacancy_management_keyboard(vacancy.id, vacancy.is_active)
        )
    else:
        await bot.send_message(
            chat_id=user_id,
            text=details_text,
            reply_markup=get_vacancy_management_keyboard(vacancy.id, vacancy.is_active)
        )


@router.callback_query(F.data.startswith("vacancy:"))
async def show_vacancy_details(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Показ деталей вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    vacancy = await crud.get_vacancy(session, vacancy_id)
    
    await callback.answer()
    
    if not vacancy:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "❌ Вакансия не найдена",
            reply_markup=get_employer_menu()
        )
        return
    
    expires = vacancy.created_at + timedelta(days=config.limits.vacancy_lifetime_days)
    
    details_text = texts.VACANCY_DETAILS.format(
        title=vacancy.title,
        city=vacancy.city,
        salary=vacancy.salary,
        description=vacancy.description,
        views=vacancy.views_count,
        responses=vacancy.responses_count,
        created=vacancy.created_at.strftime("%d.%m.%Y"),
        expires=expires.strftime("%d.%m.%Y")
    )
    
    # Добавляем статус
    status_parts = []
    if vacancy.is_active:
        status_parts.append("✅ Активна")
    else:
        status_parts.append("❌ Неактивна")
    
    if vacancy.is_pinned_now():
        status_parts.append(f"📌 Закреплена до {vacancy.pinned_until.strftime('%d.%m.%Y %H:%M')}")
    
    if vacancy.is_boosted:
        status_parts.append("🔝 Поднята")
    
    details_text += f"\n\n📊 Статус: {', '.join(status_parts)}"
    
    # Удаляем старое сообщение и показываем с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=vacancy.photo_id,
        caption=details_text,
        reply_markup=get_vacancy_management_keyboard(vacancy_id, vacancy.is_active)
    )


# ============== Управление вакансией ==============

@router.callback_query(F.data.startswith("delete_vacancy:"))
async def delete_vacancy(callback: CallbackQuery, session: AsyncSession):
    """Удаление вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    await crud.delete_vacancy(session, vacancy_id)
    await callback.answer(texts.VACANCY_DELETED)
    
    # Возвращаемся к списку
    vacancies = await crud.get_employer_vacancies(session, callback.from_user.id)
    
    # Удаляем сообщение с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    if not vacancies:
        await callback.message.answer(
            texts.MY_VACANCIES_EMPTY,
            reply_markup=get_employer_menu()
        )
    else:
        await callback.message.answer(
            "📄 Ваши вакансии:",
            reply_markup=get_my_vacancies_keyboard(vacancies)
        )


@router.callback_query(F.data.startswith("boost_vacancy:"))
async def boost_vacancy(callback: CallbackQuery, state: FSMContext):
    """Поднятие вакансии - запрос оплаты"""
    vacancy_id = int(callback.data.split(":")[1])
    await callback.answer("Переход к оплате...")
    
    # Перенаправляем на оплату
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from bot.utils import texts
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_PAY, callback_data=f"pay_boost:{vacancy_id}")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=f"vacancy:{vacancy_id}")],
    ])
    
    await callback.message.edit_caption(
        caption=texts.BOOST_CONFIRM,
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("pin_vacancy:"))
async def pin_vacancy(callback: CallbackQuery):
    """Закрепление вакансии - выбор срока"""
    vacancy_id = int(callback.data.split(":")[1])
    await callback.answer()
    
    try:
        await callback.message.edit_caption(
            caption=texts.PIN_DURATION_SELECT,
            reply_markup=get_pin_duration_keyboard(vacancy_id)
        )
    except Exception:
        # Если не получается отредактировать caption (нет фото), пробуем текст
        await callback.message.edit_text(
            texts.PIN_DURATION_SELECT,
            reply_markup=get_pin_duration_keyboard(vacancy_id)
        )


# ============== Редактирование вакансии ==============

@router.callback_query(F.data.startswith("edit_vacancy:"))
async def start_edit_vacancy(callback: CallbackQuery):
    """Начало редактирования вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    await callback.answer()
    
    try:
        await callback.message.edit_caption(
            caption="✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )
    except Exception:
        # Если не получается отредактировать caption (нет фото), пробуем текст
        await callback.message.edit_text(
            "✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )


@router.callback_query(F.data.startswith("edit_vac:"))
async def edit_vacancy_field(callback: CallbackQuery, state: FSMContext):
    """Редактирование поля вакансии"""
    parts = callback.data.split(":")
    vacancy_id = int(parts[1])
    field = parts[2]
    
    await callback.answer()
    await state.update_data(editing_vacancy_id=vacancy_id, editing_field=field)
    
    prompts = {
        "title": "Введите новое название:",
        "city": "Введите новый город:",
        "location": texts.EMPLOYER_VACANCY_LOCATION,
        "salary": "Введите новую зарплату:",
        "description": "Введите новое описание (макс 2000 символов):",
        "photo": "Отправьте новое фото:",
    }
    
    prompt = prompts.get(field, "")
    
    from bot.keyboards.employer import get_cancel_edit_vacancy_keyboard
    
    if field == "location":
        await callback.message.answer(prompt, reply_markup=get_location_keyboard())
        await state.set_state(EmployerEditStates.editing_location)
    elif field == "photo":
        try:
            await callback.message.edit_caption(caption=prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        await state.set_state(EmployerEditStates.editing_photo)
    elif field == "description":
        try:
            await callback.message.edit_caption(caption=prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        await state.set_state(EmployerEditStates.editing_description)
    elif field == "title":
        try:
            await callback.message.edit_caption(caption=prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        await state.set_state(EmployerEditStates.editing_title)
    elif field == "city":
        try:
            await callback.message.edit_caption(caption=prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        await state.set_state(EmployerEditStates.editing_city)
    elif field == "salary":
        try:
            await callback.message.edit_caption(caption=prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(prompt, reply_markup=get_cancel_edit_vacancy_keyboard(vacancy_id))
        await state.set_state(EmployerEditStates.editing_salary)


@router.callback_query(F.data.startswith("cancel_edit_vacancy:"))
async def cancel_edit_vacancy(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отмена редактирования вакансии"""
    vacancy_id = int(callback.data.split(":")[1])
    await state.clear()
    await callback.answer("Редактирование отменено")
    
    # Возвращаемся в меню редактирования вакансии
    try:
        await callback.message.edit_caption(
            caption="✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )
    except Exception:
        # Если не получается отредактировать caption (нет фото), пробуем текст
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )


@router.message(EmployerEditStates.editing_title)
async def save_edit_title(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение нового названия"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено")
        # Возвращаемся в меню редактирования
        await message.answer(
            "✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )
        return
    
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await crud.update_vacancy(session, vacancy_id, title=message.text.strip())
    await state.clear()
    await message.answer("✅ Название обновлено!", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


@router.message(EmployerEditStates.editing_city)
async def save_edit_city(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение нового города"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено")
        # Возвращаемся в меню редактирования
        try:
            await message.answer(
                "✏️ Выберите что изменить:",
                reply_markup=get_vacancy_edit_keyboard(vacancy_id)
            )
        except Exception:
            pass
        return
    
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await crud.update_vacancy(session, vacancy_id, city=message.text.strip())
    await state.clear()
    await message.answer("✅ Город обновлён!", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


@router.message(EmployerEditStates.editing_salary)
async def save_edit_salary(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение новой зарплаты"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено")
        # Возвращаемся в меню редактирования
        try:
            await message.answer(
                "✏️ Выберите что изменить:",
                reply_markup=get_vacancy_edit_keyboard(vacancy_id)
            )
        except Exception:
            pass
        return
    
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await crud.update_vacancy(session, vacancy_id, salary=message.text.strip())
    await state.clear()
    await message.answer("✅ Зарплата обновлена!", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


@router.message(EmployerEditStates.editing_description)
async def save_edit_description(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение нового описания"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено")
        # Возвращаемся в меню редактирования
        try:
            await message.answer(
                "✏️ Выберите что изменить:",
                reply_markup=get_vacancy_edit_keyboard(vacancy_id)
            )
        except Exception:
            pass
        return
    
    is_valid, error = validate_description_length(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_DESCRIPTION_TOO_LONG.format(length=len(message.text or "")))
        return
    
    await crud.update_vacancy(session, vacancy_id, description=message.text.strip())
    await state.clear()
    await message.answer("✅ Описание обновлено!", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


@router.message(EmployerEditStates.editing_location)
async def save_edit_location(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение новой геопозиции"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено", reply_markup=ReplyKeyboardRemove())
        # Возвращаемся в меню редактирования
        await message.answer(
            "✏️ Выберите что изменить:",
            reply_markup=get_vacancy_edit_keyboard(vacancy_id)
        )
        return
    
    if not message.location:
        await message.answer("Пожалуйста, отправьте геолокацию или нажмите 'Отмена'")
        return
    
    await crud.update_vacancy(
        session, vacancy_id,
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await state.clear()
    await message.answer(
        "✅ Геопозиция обновлена!",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Меню редактирования:", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


@router.message(EmployerEditStates.editing_photo)
async def save_edit_photo(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Сохранение нового фото"""
    data = await state.get_data()
    vacancy_id = data.get("editing_vacancy_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        await message.answer("Редактирование отменено")
        # Возвращаемся в меню редактирования
        try:
            await message.answer(
                "✏️ Выберите что изменить:",
                reply_markup=get_vacancy_edit_keyboard(vacancy_id)
            )
        except Exception:
            pass
        return
    
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото или нажмите 'Отмена'")
        return
    
    photo_id = message.photo[-1].file_id
    await crud.update_vacancy(session, vacancy_id, photo_id=photo_id)
    await state.clear()
    await message.answer("✅ Фото обновлено!", reply_markup=get_vacancy_edit_keyboard(vacancy_id))


# ============== Платные услуги ==============

@router.callback_query(F.data == "employer:paid_services")
async def show_paid_services(callback: CallbackQuery):
    """Показ информации о платных услугах"""
    await callback.answer()
    
    # Если предыдущее сообщение было с фото, удаляем его и отправляем новое
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            texts.PAID_SERVICES,
            reply_markup=get_paid_services_keyboard()
        )
    else:
        await callback.message.edit_text(
            texts.PAID_SERVICES,
            reply_markup=get_paid_services_keyboard()
        )


@router.callback_query(F.data == "employer:my_payments")
async def show_my_payments(callback: CallbackQuery, session: AsyncSession):
    """Показ истории покупок работодателя"""
    await callback.answer()
    
    user_id = callback.from_user.id
    payments = await crud.get_user_payments(session, user_id)
    
    if not payments:
        text = "📋 История покупок\n\nУ вас пока нет покупок."
    else:
        text = "📋 История покупок:\n\n"
        for payment in payments[:20]:  # Последние 20
            status = "✅ Оплачено" if payment.is_confirmed else "⏳ Ожидает"
            date_str = payment.created_at.strftime("%d.%m.%Y %H:%M")
            
            payment_type_names = {
                "vacancy_publication": "📌 Публикация вакансии",
                "vacancy_boost": "🔝 Поднятие вакансии",
                "vacancy_pin_1d": "📍 Закрепление (1 день)",
                "vacancy_pin_3d": "📍 Закрепление (3 дня)",
                "vacancy_pin_7d": "📍 Закрепление (7 дней)",
            }
            
            payment_name = payment_type_names.get(payment.payment_type, payment.payment_type)
            text += f"{payment_name}\n"
            text += f"{status} | {payment.amount} ₽ | {date_str}\n\n"
    
    # Если предыдущее сообщение было с фото, удаляем его
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=get_paid_services_keyboard())
    else:
        await callback.message.edit_text(text, reply_markup=get_paid_services_keyboard())
