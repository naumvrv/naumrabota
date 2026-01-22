import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    token: str


@dataclass
class DatabaseConfig:
    url: str


@dataclass
class PaymentConfig:
    shop_id: str
    secret_key: str
    return_url: str
    webhook_path: str = "/yookassa/webhook"


@dataclass
class AdminConfig:
    admin_id: int
    support_email: str


@dataclass
class PriceConfig:
    """Цены на услуги в рублях"""
    worker_subscription: int = 300  # Подписка работника в месяц
    vacancy_publication: int = 100  # Публикация вакансии сверх лимита
    vacancy_boost: int = 200  # Поднятие вакансии
    vacancy_pin_1d: int = 100  # Закрепление на 1 день
    vacancy_pin_3d: int = 250  # Закрепление на 3 дня
    vacancy_pin_7d: int = 500  # Закрепление на 7 дней


@dataclass
class LimitConfig:
    """Лимиты для пользователей"""
    daily_vacancy_views: int = 25  # Просмотров вакансий в сутки для бесплатных
    free_vacancies_per_month: int = 2  # Бесплатных вакансий в месяц
    vacancy_lifetime_days: int = 30  # Срок жизни вакансии в днях
    max_resume_length: int = 1000  # Максимальная длина резюме
    max_description_length: int = 2000  # Максимальная длина описания вакансии
    geo_filter_radius_km: int = 50  # Радиус геофильтрации в км


@dataclass
class GeocodingConfig:
    """Конфигурация геокодинга"""
    api_key: str = ""  # API ключ Яндекс.Геокодера
    web_app_url: str = ""  # URL для Telegram Web App выбора местоположения


@dataclass
class Config:
    bot: BotConfig
    db: DatabaseConfig
    payment: PaymentConfig
    admin: AdminConfig
    prices: PriceConfig
    limits: LimitConfig
    geocoding: GeocodingConfig


def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения"""
    # По умолчанию используем SQLite для локального тестирования
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        db_url = "sqlite+aiosqlite:///./botrabota.db"
    
    return Config(
        bot=BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
        ),
        db=DatabaseConfig(
            url=db_url,
        ),
        payment=PaymentConfig(
            shop_id=os.getenv("YOOKASSA_SHOP_ID", ""),
            secret_key=os.getenv("YOOKASSA_SECRET_KEY", ""),
            return_url=os.getenv("YOOKASSA_RETURN_URL", ""),
        ),
        admin=AdminConfig(
            admin_id=int(os.getenv("ADMIN_ID", "411655143")),
            support_email=os.getenv("SUPPORT_EMAIL", "vnaum0134@gmail.com"),
        ),
        prices=PriceConfig(),
        limits=LimitConfig(),
        geocoding=GeocodingConfig(
            api_key=os.getenv("YANDEX_GEOCODER_API_KEY", ""),
            web_app_url=os.getenv("WEB_APP_URL", "https://naumrabota.ru/web_apps/location_picker.html"),
        ),
    )


# Глобальный экземпляр конфигурации
config = load_config()
