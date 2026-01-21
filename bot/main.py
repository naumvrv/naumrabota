"""Главный файл бота - точка входа"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database.connection import init_db, close_db
from bot.middlewares.db_middleware import DatabaseMiddleware
from bot.handlers import (
    start_router,
    worker_router,
    employer_router,
    admin_router,
    payments_router,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных инициализирована")
    
    # Уведомление админа о запуске
    try:
        await bot.send_message(
            config.admin.admin_id,
            "🟢 Бот запущен и готов к работе!"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа о запуске: {e}")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Завершение работы...")
    
    # Уведомление админа об остановке
    try:
        await bot.send_message(
            config.admin.admin_id,
            "🔴 Бот остановлен"
        )
    except Exception:
        pass
    
    await close_db()
    logger.info("Соединение с БД закрыто")


async def main():
    """Главная функция запуска бота"""
    # Проверка токена
    if not config.bot.token:
        logger.error("BOT_TOKEN не установлен! Проверьте .env файл")
        return
    
    # Создание бота
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Создание диспетчера
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.pre_checkout_query.middleware(DatabaseMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(worker_router)
    dp.include_router(employer_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    
    # Регистрация startup/shutdown хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Запуск бота...")
    
    try:
        # Удаление вебхука и запуск polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
