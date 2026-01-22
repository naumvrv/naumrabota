"""Утилита для управления сообщениями и их автоматической очистки"""

import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

# Максимальное количество хранимых ID сообщений
MAX_MESSAGE_IDS = 20


class MessageManager:
    """Класс для управления ID сообщений и их автоматической очистки"""
    
    @staticmethod
    async def add_message_id(
        state: FSMContext,
        message_id: int,
        is_vacancy: bool = False
    ) -> None:
        """
        Добавление ID сообщения в FSM state
        
        Args:
            state: FSM контекст
            message_id: ID сообщения
            is_vacancy: Является ли сообщение вакансией (не удалять)
        """
        data = await state.get_data()
        
        if is_vacancy:
            vacancy_ids: List[int] = data.get("vacancy_message_ids", [])
            if message_id not in vacancy_ids:
                vacancy_ids.append(message_id)
                # Ограничиваем количество хранимых ID
                if len(vacancy_ids) > MAX_MESSAGE_IDS:
                    vacancy_ids = vacancy_ids[-MAX_MESSAGE_IDS:]
                await state.update_data(vacancy_message_ids=vacancy_ids)
        else:
            message_ids: List[int] = data.get("message_ids", [])
            if message_id not in message_ids:
                message_ids.append(message_id)
                # Ограничиваем количество хранимых ID
                if len(message_ids) > MAX_MESSAGE_IDS:
                    message_ids = message_ids[-MAX_MESSAGE_IDS:]
                await state.update_data(message_ids=message_ids)
    
    @staticmethod
    async def mark_vacancy_message(
        state: FSMContext,
        message_id: int
    ) -> None:
        """
        Пометка сообщения как вакансии (не удалять)
        
        Args:
            state: FSM контекст
            message_id: ID сообщения
        """
        await MessageManager.add_message_id(state, message_id, is_vacancy=True)
    
    @staticmethod
    async def cleanup_old_messages(
        bot: Bot,
        chat_id: int,
        state: FSMContext
    ) -> None:
        """
        Удаление старых сообщений (кроме вакансий)
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            state: FSM контекст
        """
        data = await state.get_data()
        message_ids: List[int] = data.get("message_ids", [])
        vacancy_ids: List[int] = data.get("vacancy_message_ids", [])
        
        if not message_ids:
            return
        
        # Удаляем сообщения параллельно
        import asyncio
        
        async def delete_message(msg_id: int):
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                # Игнорируем ошибки (сообщение уже удалено, бот не может удалить и т.д.)
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
        
        # Удаляем только обычные сообщения (не вакансии)
        tasks = [delete_message(msg_id) for msg_id in message_ids if msg_id not in vacancy_ids]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Очищаем список удаленных сообщений
        await state.update_data(message_ids=[])
    
    @staticmethod
    async def clear_all(state: FSMContext) -> None:
        """
        Очистка всех ID сообщений (при смене контекста)
        
        Args:
            state: FSM контекст
        """
        await state.update_data(message_ids=[], vacancy_message_ids=[])
    
    @staticmethod
    async def get_message_ids(state: FSMContext) -> tuple[List[int], List[int]]:
        """
        Получение списков ID сообщений
        
        Returns:
            tuple: (обычные сообщения, сообщения вакансий)
        """
        data = await state.get_data()
        return (
            data.get("message_ids", []),
            data.get("vacancy_message_ids", [])
        )
