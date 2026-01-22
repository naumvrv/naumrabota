"""SQLAlchemy модели базы данных"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import BigInteger, String, Text, Float, Integer, Boolean, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'worker' или 'employer'
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resume: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Подписка
    subscription_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Лимиты просмотров для работника
    daily_views: Mapped[int] = mapped_column(Integer, default=0)
    last_view_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Лимиты вакансий для работодателя
    free_vacancies_left: Mapped[int] = mapped_column(Integer, default=2)
    vacancies_reset_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Блокировка
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    vacancies: Mapped[list["Vacancy"]] = relationship("Vacancy", back_populates="employer")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
    
    def has_active_subscription(self) -> bool:
        """Проверка активной подписки"""
        if self.subscription_until is None:
            return False
        return self.subscription_until > datetime.utcnow()
    
    def is_resume_complete(self) -> bool:
        """Проверка заполненности резюме"""
        return all([
            self.name,
            self.age is not None,
            self.city,
            self.latitude is not None,
            self.longitude is not None,
            self.resume,
            self.photo_id
        ])


class Vacancy(Base):
    """Модель вакансии"""
    __tablename__ = "vacancies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    title: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    salary: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    photo_id: Mapped[str] = mapped_column(String(200))
    
    # Статистика
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    responses_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Продвижение
    is_boosted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    employer: Mapped["User"] = relationship("User", back_populates="vacancies")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="vacancy")
    
    def is_pinned_now(self) -> bool:
        """Проверка активного закрепления"""
        if not self.is_pinned or self.pinned_until is None:
            return False
        return self.pinned_until > datetime.utcnow()


class Payment(Base):
    """Модель платежа"""
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    vacancy_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vacancies.id"), nullable=True)
    
    payment_type: Mapped[str] = mapped_column(String(50))  # worker_subscription, vacancy_publication, etc.
    amount: Mapped[int] = mapped_column(Integer)  # в рублях
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, succeeded, canceled
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    yookassa_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="payments")
    vacancy: Mapped[Optional["Vacancy"]] = relationship("Vacancy", back_populates="payments")


class AdminLog(Base):
    """Модель логов администратора"""
    __tablename__ = "admin_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
