"""Middleware для автоматической очистки старых сообщений"""

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.utils.message_manager import MessageManager
from bot.keyboards.worker import get_vacancy_buttons

logger = logging.getLogger(__name__)


class MessageCleanupMiddleware(BaseMiddleware):
    """Middleware для автоматической очистки старых сообщений (кроме вакансий)"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем FSM context и bot из data
        state: FSMContext = data.get("state")
        bot: Bot = data.get("bot")
        
        # Выполняем хендлер
        result = await handler(event, data)
        
        # Если нет state или bot, пропускаем обработку
        if not state or not bot:
            return result
        
        # Обрабатываем только Message и CallbackQuery
        if isinstance(event, (Message, CallbackQuery)):
            try:
                # Определяем chat_id
                if isinstance(event, Message):
                    chat_id = event.chat.id
                else:  # CallbackQuery
                    chat_id = event.message.chat.id
                
                # Проверяем, является ли результат отправленным сообщением
                if isinstance(result, Message):
                    sent_message = result
                    is_vacancy = self._is_vacancy_message(sent_message)
                    
                    # Очищаем старые сообщения после отправки нового (если не вакансия)
                    # Это нормально - пользователь увидит новое сообщение, а старые удалятся сразу после
                    if not is_vacancy:
                        await MessageManager.cleanup_old_messages(bot, chat_id, state)
                    
                    # Добавляем ID нового сообщения
                    await MessageManager.add_message_id(
                        state,
                        sent_message.message_id,
                        is_vacancy=is_vacancy
                    )
                
            except Exception as e:
                # Логируем ошибку, но не прерываем работу бота
                logger.error(f"Ошибка в MessageCleanupMiddleware: {e}", exc_info=True)
        
        return result
    
    @staticmethod
    def _is_vacancy_message(message: Message) -> bool:
        """
        Определяет, является ли сообщение вакансией
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если сообщение является вакансией
        """
        # Проверяем наличие клавиатуры с кнопками вакансии
        if message.reply_markup:
            # Проверяем inline клавиатуру
            if hasattr(message.reply_markup, 'inline_keyboard'):
                inline_keyboard = message.reply_markup.inline_keyboard
                if inline_keyboard:
                    # Проверяем наличие кнопок "Откликнуться" и "Следующая вакансия"
                    for row in inline_keyboard:
                        for button in row:
                            if hasattr(button, 'callback_data'):
                                callback_data = button.callback_data
                                if callback_data:
                                    # Проверяем на наличие кнопок вакансии
                                    if (callback_data.startswith("respond:") or 
                                        callback_data == "next_vacancy"):
                                        return True
        
        # Также проверяем по тексту сообщения (сообщения об отклике)
        if message.text:
            text = message.text.lower()
            if ("отправляем отклик" in text or 
                "отклик отправлен" in text or
                "отклик отправлен" in text):
                return True
        
        return False
