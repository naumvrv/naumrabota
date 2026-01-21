"""Геолокационные сервисы - расчет расстояний по формуле Хаверсина"""

import math
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Vacancy
from bot.database import crud
from bot.config import config


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Расчет расстояния между двумя точками по формуле Хаверсина.
    
    Args:
        lat1, lon1: Координаты первой точки (широта, долгота)
        lat2, lon2: Координаты второй точки (широта, долгота)
    
    Returns:
        Расстояние в километрах
    """
    R = 6371  # Радиус Земли в километрах
    
    # Преобразование градусов в радианы
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Формула Хаверсина
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


async def get_nearby_vacancies(
    session: AsyncSession,
    worker_lat: float,
    worker_lon: float,
    max_distance: float | None = None
) -> list[tuple[Vacancy, float]]:
    """
    Получение вакансий в радиусе от работника.
    
    Args:
        session: Сессия БД
        worker_lat: Широта работника
        worker_lon: Долгота работника
        max_distance: Максимальное расстояние в км (по умолчанию из конфига)
    
    Returns:
        Список кортежей (Vacancy, distance) отсортированный по приоритету
    """
    if max_distance is None:
        max_distance = config.limits.geo_filter_radius_km
    
    all_vacancies = await crud.get_active_vacancies(session)
    nearby = []
    
    for vacancy in all_vacancies:
        distance = calculate_distance(
            worker_lat, worker_lon,
            vacancy.latitude, vacancy.longitude
        )
        if distance <= max_distance:
            nearby.append((vacancy, distance))
    
    # Сортировка: сначала закрепленные, потом поднятые, потом по дате
    def sort_key(item: tuple[Vacancy, float]) -> tuple:
        vacancy, _ = item
        return (
            not vacancy.is_pinned_now(),  # False первее True, так что pinned идут первыми
            not vacancy.is_boosted,
            vacancy.created_at  # Старые раньше
        )
    
    nearby.sort(key=sort_key)
    
    # Меняем порядок чтобы новые были раньше
    nearby.sort(key=lambda x: (
        not x[0].is_pinned_now(),
        not x[0].is_boosted,
        -x[0].created_at.timestamp()  # Новые раньше
    ))
    
    return nearby
