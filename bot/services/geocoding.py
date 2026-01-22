"""Сервис геокодинга - преобразование адреса в координаты через Яндекс.Геокодер API"""

import aiohttp
from typing import Optional, Tuple
from bot.config import config


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Преобразование адреса в координаты через Яндекс.Геокодер API.
    
    Args:
        address: Адрес в виде строки (например, "Москва, ул. Ленина, д. 10")
    
    Returns:
        Кортеж (широта, долгота) или None, если адрес не найден
    """
    if not config.geocoding.api_key:
        return None
    
    if not address or not address.strip():
        return None
    
    url = "https://geocode-maps.yandex.ru/1.x/"
    
    params = {
        "apikey": config.geocoding.api_key,
        "geocode": address.strip(),
        "format": "json",
        "results": 1,
        "lang": "ru_RU"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                # Проверяем наличие результатов
                if "response" not in data:
                    return None
                
                response_data = data["response"]
                if "GeoObjectCollection" not in response_data:
                    return None
                
                geo_objects = response_data["GeoObjectCollection"]
                if "featureMember" not in geo_objects or not geo_objects["featureMember"]:
                    return None
                
                # Берем первый результат
                first_result = geo_objects["featureMember"][0]
                if "GeoObject" not in first_result:
                    return None
                
                geo_object = first_result["GeoObject"]
                if "Point" not in geo_object or "pos" not in geo_object["Point"]:
                    return None
                
                # Парсим координаты (формат: "долгота широта")
                pos_str = geo_object["Point"]["pos"]
                lon, lat = map(float, pos_str.split())
                
                # Валидация координат
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    return None
                
                return (lat, lon)
                
    except Exception:
        # В случае любой ошибки возвращаем None
        return None


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Обратное геокодирование - преобразование координат в адрес.
    
    Args:
        lat: Широта
        lon: Долгота
    
    Returns:
        Адрес в виде строки или None, если не удалось определить
    """
    if not config.geocoding.api_key:
        return None
    
    url = "https://geocode-maps.yandex.ru/1.x/"
    
    params = {
        "apikey": config.geocoding.api_key,
        "geocode": f"{lon},{lat}",
        "format": "json",
        "results": 1,
        "lang": "ru_RU",
        "kind": "house"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                if "response" not in data:
                    return None
                
                response_data = data["response"]
                if "GeoObjectCollection" not in response_data:
                    return None
                
                geo_objects = response_data["GeoObjectCollection"]
                if "featureMember" not in geo_objects or not geo_objects["featureMember"]:
                    return None
                
                first_result = geo_objects["featureMember"][0]
                if "GeoObject" not in first_result:
                    return None
                
                geo_object = first_result["GeoObject"]
                if "metaDataProperty" not in geo_object:
                    return None
                
                meta_data = geo_object["metaDataProperty"]
                if "GeocoderMetaData" not in meta_data:
                    return None
                
                geocoder_meta = meta_data["GeocoderMetaData"]
                if "text" not in geocoder_meta:
                    return None
                
                return geocoder_meta["text"]
                
    except Exception:
        return None
