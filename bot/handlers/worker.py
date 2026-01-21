"""Хендлеры для работника"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import crud
from bot.database.models import Vacancy
from bot.keyboards.common import get_location_keyboard
from bot.keyboards.worker import (
    get_worker_menu,
    get_vacancy_buttons,
    get_limit_reached_keyboard,
    get_subscription_keyboard,
    get_start_search_keyboard,
    get_resume_edit_keyboard,
    get_no_vacancies_keyboard,
)
from bot.utils import texts
from bot.utils.validators import validate_age, validate_resume_length, validate_not_empty
from bot.states.worker_states import WorkerStates, WorkerEditStates
from bot.services.geo import get_nearby_vacancies, calculate_distance
from bot.services.limits import check_daily_view_limit
from bot.config import config

router = Router(name="worker")


# ============== FSM: Создание резюме ==============

@router.message(WorkerStates.waiting_for_name)
async def process_name(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка имени"""
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await state.update_data(name=message.text.strip())
    await message.answer(texts.WORKER_RESUME_AGE)
    await state.set_state(WorkerStates.waiting_for_age)


@router.message(WorkerStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    """Обработка возраста"""
    is_valid, age, error = validate_age(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_INVALID_AGE)
        return
    
    await state.update_data(age=age)
    await message.answer(texts.WORKER_RESUME_CITY)
    await state.set_state(WorkerStates.waiting_for_city)


@router.message(WorkerStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    """Обработка города"""
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await state.update_data(city=message.text.strip())
    await message.answer(
        texts.WORKER_RESUME_LOCATION,
        reply_markup=get_location_keyboard()
    )
    await state.set_state(WorkerStates.waiting_for_location)


@router.message(WorkerStates.waiting_for_location, F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка геопозиции"""
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await message.answer(
        texts.WORKER_RESUME_TEXT,
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(WorkerStates.waiting_for_resume)


@router.message(WorkerStates.waiting_for_location)
async def process_location_invalid(message: Message):
    """Некорректная геопозиция"""
    await message.answer(
        texts.ERROR_NOT_LOCATION,
        reply_markup=get_location_keyboard()
    )


@router.message(WorkerStates.waiting_for_resume)
async def process_resume(message: Message, state: FSMContext):
    """Обработка текста резюме"""
    is_valid, error = validate_resume_length(message.text or "")
    if not is_valid:
        await message.answer(
            texts.ERROR_RESUME_TOO_LONG.format(length=len(message.text or ""))
        )
        return
    
    await state.update_data(resume=message.text.strip())
    await message.answer(texts.WORKER_RESUME_PHOTO)
    await state.set_state(WorkerStates.waiting_for_photo)


@router.message(WorkerStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка фото"""
    photo_id = message.photo[-1].file_id  # Берем фото наилучшего качества
    
    data = await state.get_data()
    
    # Сохраняем данные в БД
    await crud.update_user(
        session,
        message.from_user.id,
        name=data.get("name"),
        age=data.get("age"),
        city=data.get("city"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        resume=data.get("resume"),
        photo_id=photo_id,
    )
    
    await state.clear()
    await message.answer(
        texts.WORKER_RESUME_SAVED,
        reply_markup=get_start_search_keyboard()
    )


@router.message(WorkerStates.waiting_for_photo)
async def process_photo_invalid(message: Message):
    """Некорректное фото"""
    await message.answer(texts.ERROR_NOT_PHOTO)


# ============== Редактирование резюме ==============

@router.callback_query(F.data == "worker:edit_resume")
async def show_edit_resume(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Показ меню редактирования резюме"""
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer()
    
    if not user or not user.is_resume_complete():
        await callback.message.edit_text(texts.WORKER_RESUME_START)
        return
    
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    # Удаляем старое сообщение и отправляем новое с фото
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=user.photo_id,
        caption=resume_preview,
        reply_markup=get_resume_edit_keyboard()
    )


@router.callback_query(F.data == "worker:cancel_edit")
async def cancel_edit_resume(callback: CallbackQuery, session: AsyncSession, bot: Bot, state: FSMContext):
    """Отмена редактирования резюме"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    await state.clear()
    await callback.answer("Редактирование отменено")
    
    user = await crud.get_user(session, callback.from_user.id)
    
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    # Пытаемся отредактировать существующее сообщение
    if resume_message_id:
        try:
            await bot.edit_message_caption(
                chat_id=callback.message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
            return
        except Exception:
            pass
    
    # Если не получилось, удаляем старое и отправляем новое
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=user.photo_id,
        caption=resume_preview,
        reply_markup=get_resume_edit_keyboard()
    )


@router.callback_query(F.data.startswith("edit_resume:"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поля резюме"""
    from bot.keyboards.worker import get_cancel_keyboard
    
    field = callback.data.split(":")[1]
    await callback.answer()
    
    prompts = {
        "name": ("Введите новое имя:", WorkerEditStates.editing_name),
        "age": ("Введите новый возраст (14-80):", WorkerEditStates.editing_age),
        "city": ("Введите новый город:", WorkerEditStates.editing_city),
        "location": (texts.WORKER_RESUME_LOCATION, WorkerEditStates.editing_location),
        "resume": ("Введите новый текст резюме (макс 1000 символов):", WorkerEditStates.editing_resume),
        "photo": ("Отправьте новое фото:", WorkerEditStates.editing_photo),
    }
    
    prompt, state_obj = prompts.get(field, ("", None))
    if state_obj:
        # Сохраняем ID сообщения с резюме для последующего редактирования
        await state.update_data(resume_message_id=callback.message.message_id)
        
        if field == "location":
            await callback.message.answer(prompt, reply_markup=get_location_keyboard())
        else:
            # Проверяем, есть ли фото в сообщении
            if callback.message.photo:
                try:
                    await callback.message.edit_caption(
                        caption=prompt,
                        reply_markup=get_cancel_keyboard()
                    )
                except Exception:
                    # Если не получилось отредактировать, удаляем и отправляем новое
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    new_msg = await callback.message.answer(prompt, reply_markup=get_cancel_keyboard())
                    await state.update_data(resume_message_id=new_msg.message_id)
            else:
                await callback.message.edit_text(prompt, reply_markup=get_cancel_keyboard())
        await state.set_state(state_obj)


@router.message(WorkerEditStates.editing_name)
async def edit_name(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование имени"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass
        
        # Редактируем сообщение с резюме
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await crud.update_user(session, message.from_user.id, name=message.text.strip())
    await state.clear()
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
    
    # Показываем обновленное резюме
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    # Редактируем сообщение с резюме
    try:
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=resume_message_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )
    except Exception:
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=user.photo_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )


@router.message(WorkerEditStates.editing_age)
async def edit_age(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование возраста"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    is_valid, age, error = validate_age(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_INVALID_AGE)
        return
    
    await crud.update_user(session, message.from_user.id, age=age)
    await state.clear()
    
    try:
        await message.delete()
    except Exception:
        pass
    
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    try:
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=resume_message_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )
    except Exception:
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=user.photo_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )


@router.message(WorkerEditStates.editing_city)
async def edit_city(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование города"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    is_valid, error = validate_not_empty(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_EMPTY_TEXT)
        return
    
    await crud.update_user(session, message.from_user.id, city=message.text.strip())
    await state.clear()
    
    try:
        await message.delete()
    except Exception:
        pass
    
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    try:
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=resume_message_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )
    except Exception:
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=user.photo_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )


@router.message(WorkerEditStates.editing_location)
async def edit_location(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование геопозиции"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    if not message.location:
        await message.answer("Пожалуйста, отправьте геолокацию или нажмите 'Отмена'", reply_markup=ReplyKeyboardRemove())
        return
    
    await crud.update_user(
        session, message.from_user.id,
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    await state.clear()
    
    try:
        await message.delete()
    except Exception:
        pass
    
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    try:
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=resume_message_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )
    except Exception:
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=user.photo_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )


@router.message(WorkerEditStates.editing_resume)
async def edit_resume_text(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование текста резюме"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    is_valid, error = validate_resume_length(message.text or "")
    if not is_valid:
        await message.answer(texts.ERROR_RESUME_TOO_LONG.format(length=len(message.text or "")))
        return
    
    await crud.update_user(session, message.from_user.id, resume=message.text.strip())
    await state.clear()
    
    try:
        await message.delete()
    except Exception:
        pass
    
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    try:
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=resume_message_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )
    except Exception:
        await bot.send_photo(
            chat_id=message.from_user.id,
            photo=user.photo_id,
            caption=resume_preview,
            reply_markup=get_resume_edit_keyboard()
        )


@router.message(WorkerEditStates.editing_photo)
async def edit_photo(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    """Редактирование фото"""
    data = await state.get_data()
    resume_message_id = data.get("resume_message_id")
    
    # Проверка на отмену
    if message.text and message.text.strip() == "❌ Отмена":
        await state.clear()
        
        user = await crud.get_user(session, message.from_user.id)
        resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
        
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=resume_message_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        except Exception:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=user.photo_id,
                caption=resume_preview,
                reply_markup=get_resume_edit_keyboard()
            )
        return
    
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото или нажмите 'Отмена'")
        return
    
    photo_id = message.photo[-1].file_id
    await crud.update_user(session, message.from_user.id, photo_id=photo_id)
    await state.clear()
    
    user = await crud.get_user(session, message.from_user.id)
    resume_preview = f"""📝 Ваше резюме:

👤 Имя: {user.name}
🎂 Возраст: {user.age}
🏙 Город: {user.city}
📝 О себе: {user.resume[:100]}{"..." if len(user.resume or "") > 100 else ""}

Выберите что изменить:"""
    
    # Для фото нужно удалить старое сообщение и отправить новое с обновленным фото
    try:
        await message.delete()
        await bot.delete_message(chat_id=message.chat.id, message_id=resume_message_id)
    except Exception:
        pass
    
    await bot.send_photo(
        chat_id=message.from_user.id,
        photo=user.photo_id,
        caption=resume_preview,
        reply_markup=get_resume_edit_keyboard()
    )


@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    await state.clear()
    await callback.answer("❌ Редактирование отменено")
    await callback.message.answer(texts.WORKER_MENU, reply_markup=get_worker_menu())


# ============== Меню работника ==============

@router.callback_query(F.data == "worker:menu")
async def show_worker_menu(callback: CallbackQuery, state: FSMContext):
    """Показ меню работника"""
    await state.clear()
    await callback.answer()
    
    # Проверяем, есть ли фото в сообщении
    if callback.message.photo:
        try:
            # Удаляем сообщение с фото
            await callback.message.delete()
        except Exception:
            pass
        # Отправляем новое текстовое сообщение
        await callback.message.answer(
            texts.WORKER_MENU,
            reply_markup=get_worker_menu()
        )
    else:
        await callback.message.edit_text(
            texts.WORKER_MENU,
            reply_markup=get_worker_menu()
        )


# ============== Просмотр вакансий ==============

@router.callback_query(F.data == "worker:view_vacancies")
async def start_viewing_vacancies(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Начало просмотра вакансий"""
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer()
    
    if not user:
        return
    
    # Проверка заполненности резюме
    if not user.is_resume_complete():
        await callback.message.edit_text(texts.WORKER_RESUME_START)
        await state.set_state(WorkerStates.waiting_for_name)
        return
    
    # Сброс индекса
    await crud.update_user(session, user.telegram_id, current_index=0)
    
    await show_next_vacancy(callback.message, session, user.telegram_id, edit=True)


@router.callback_query(F.data == "next_vacancy")
async def next_vacancy(callback: CallbackQuery, session: AsyncSession):
    """Показ следующей вакансии"""
    await callback.answer()
    await show_next_vacancy(callback.message, session, callback.from_user.id, edit=True)


async def show_next_vacancy(
    message: Message,
    session: AsyncSession,
    user_id: int,
    edit: bool = False
):
    """Показ следующей подходящей вакансии"""
    user = await crud.get_user(session, user_id)
    if not user or not user.latitude or not user.longitude:
        if edit:
            await message.edit_text(
                "❌ Сначала заполните резюме с геопозицией!",
                reply_markup=get_worker_menu()
            )
        else:
            await message.answer(
                "❌ Сначала заполните резюме с геопозицией!",
                reply_markup=get_worker_menu()
            )
        return
    
    # Проверка лимита просмотров
    can_view, remaining = await check_daily_view_limit(session, user_id)
    if not can_view:
        if edit:
            await message.edit_text(
                texts.VIEW_LIMIT_REACHED,
                reply_markup=get_limit_reached_keyboard()
            )
        else:
            await message.answer(
                texts.VIEW_LIMIT_REACHED,
                reply_markup=get_limit_reached_keyboard()
            )
        return
    
    # Получение вакансий в радиусе
    nearby_vacancies = await get_nearby_vacancies(
        session,
        user.latitude,
        user.longitude
    )
    
    if not nearby_vacancies:
        if edit:
            await message.edit_text(
                texts.VACANCY_NO_MORE,
                reply_markup=get_no_vacancies_keyboard()
            )
        else:
            await message.answer(
                texts.VACANCY_NO_MORE,
                reply_markup=get_no_vacancies_keyboard()
            )
        return
    
    # Получение текущего индекса
    current_index = user.current_index or 0
    
    # Если дошли до конца - начинаем сначала
    if current_index >= len(nearby_vacancies):
        current_index = 0
    
    vacancy, distance = nearby_vacancies[current_index]
    
    # Обновляем индекс
    await crud.update_user(session, user_id, current_index=current_index + 1)
    
    # Увеличиваем счетчик просмотров
    await crud.increment_vacancy_views(session, vacancy.id)
    
    # Сбрасываем boost после показа
    if vacancy.is_boosted:
        await crud.reset_vacancy_boost(session, vacancy.id)
    
    # Формируем сообщение
    vacancy_text = texts.VACANCY_VIEW_TEMPLATE.format(
        title=vacancy.title,
        city=vacancy.city,
        distance=distance,
        salary=vacancy.salary,
        description=vacancy.description
    )
    
    # Отправляем фото с текстом
    try:
        # Удаляем старое сообщение
        if edit:
            await message.delete()
    except Exception:
        pass
    
    await message.answer_photo(
        photo=vacancy.photo_id,
        caption=vacancy_text,
        reply_markup=get_vacancy_buttons(vacancy.id)
    )


# ============== Отклик на вакансию ==============

@router.callback_query(F.data.startswith("respond:"))
async def respond_to_vacancy(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Отклик на вакансию"""
    vacancy_id = int(callback.data.split(":")[1])
    user = await crud.get_user(session, callback.from_user.id)
    vacancy = await crud.get_vacancy(session, vacancy_id)
    
    if not user or not vacancy:
        await callback.answer("Ошибка! Вакансия не найдена.")
        return
    
    await callback.answer("Отправляем отклик...")
    
    # Увеличиваем счетчик откликов
    await crud.increment_vacancy_responses(session, vacancy_id)
    
    # Рассчитываем расстояние
    distance = calculate_distance(
        user.latitude, user.longitude,
        vacancy.latitude, vacancy.longitude
    )
    
    # Формируем сообщение для работодателя
    response_text = texts.NEW_RESPONSE_TEMPLATE.format(
        vacancy_title=vacancy.title,
        name=user.name,
        age=user.age,
        city=user.city,
        distance=distance,
        resume=user.resume
    )
    
    # Отправляем работодателю
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        chat_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=texts.BTN_OPEN_CHAT,
                url=f"tg://user?id={user.telegram_id}"
            )]
        ])
        
        await bot.send_photo(
            vacancy.employer_id,
            photo=user.photo_id,
            caption=response_text,
            reply_markup=chat_keyboard
        )
    except Exception as e:
        pass  # Работодатель мог заблокировать бота
    
    # Уведомляем работника
    await callback.message.answer(texts.RESPONSE_SENT)
    
    # Показываем следующую вакансию
    await show_next_vacancy(callback.message, session, callback.from_user.id, edit=False)


# ============== Подписка ==============

@router.callback_query(F.data == "worker:subscription")
async def show_subscription(callback: CallbackQuery, session: AsyncSession):
    """Показ информации о подписке"""
    user = await crud.get_user(session, callback.from_user.id)
    await callback.answer()
    
    if user and user.has_active_subscription():
        status = texts.SUBSCRIPTION_ACTIVE.format(
            date=user.subscription_until.strftime("%d.%m.%Y")
        )
    else:
        status = texts.SUBSCRIPTION_INACTIVE
    
    await callback.message.edit_text(
        texts.SUBSCRIPTION_INFO.format(status=status),
        reply_markup=get_subscription_keyboard()
    )
