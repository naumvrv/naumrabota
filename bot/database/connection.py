"""Подключение к базе данных"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from bot.config import config
from bot.database.models import Base


# Создание асинхронного движка
# Для SQLite не используем параметры пула
engine_args = {
    "echo": False,  # Установите True для отладки SQL запросов
}

# Добавляем параметры пула только для PostgreSQL
if "postgresql" in config.db.url:
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20

engine = create_async_engine(config.db.url, **engine_args)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Инициализация базы данных - создание всех таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Закрытие соединения с базой данных"""
    await engine.dispose()
