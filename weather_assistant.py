import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import requests


# =====================================================================
# 1. ВНУТРІШНЯ МОДЕЛЬ ДАНИХ (Domain Model)
# =====================================================================
@dataclass
class WeatherInterval:
    time: str
    temperature_c: float
    precipitation_probability: int


@dataclass
class WeatherForecast:
    city: str
    latitude: float
    longitude: float
    intervals: List[WeatherInterval]
    retrieved_at: str
    source: str = "Open-Meteo"


# =====================================================================
# 2. ШАБЛОН ADAPTER
# =====================================================================
class WeatherAdapter:
    """Адаптер для перетворення сирого JSON від Open-Meteo у WeatherForecast."""

    @staticmethod
    def normalize(city: str, lat: float, lon: float, raw_json: dict) -> WeatherForecast:
        if not isinstance(raw_json, dict) or "hourly" not in raw_json:
            raise ValueError("Некоректний формат відповіді API: відсутнє поле 'hourly'")

        hourly = raw_json["hourly"]
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        precips = hourly.get("precipitation_probability", [])

        length = min(len(times), len(temps), len(precips))
        if length == 0:
            raise ValueError("Відповідь API не містить погодних інтервалів")

        now_hour = datetime.now().strftime("%Y-%m-%dT%H:00")

        # Фільтруємо актуальні години (від поточної)
        intervals = [
            WeatherInterval(
                time=times[i],
                temperature_c=float(temps[i]),
                precipitation_probability=int(precips[i]),
            )
            for i in range(length)
            if times[i] >= now_hour
        ]

        # Якщо всі інтервали за добу вже минули, залишаємо останні доступні
        if not intervals:
            intervals = [
                WeatherInterval(times[i], float(temps[i]), int(precips[i]))
                for i in range(max(0, length - 3), length)
            ]

        return WeatherForecast(
            city=city,
            latitude=lat,
            longitude=lon,
            intervals=intervals,
            retrieved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


# =====================================================================
# 3. ШАБЛОН STRATEGY
# =====================================================================
class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, forecast: WeatherForecast) -> str:
        """Спільний інтерфейс для аналізу моделі та формування рекомендацій."""
        pass


class WalkStrategy(RecommendationStrategy):
    """Стратегія 1: Планування прогулянки."""

    def recommend(self, forecast: WeatherForecast) -> str:
        intervals = forecast.intervals[:3]
        if not intervals:
            return "⚠️ Недостатньо даних для розрахунку рекомендацій."

        avg_temp = sum(i.temperature_c for i in intervals) / len(intervals)
        max_rain = max(i.precipitation_probability for i in intervals)

        if max_rain >= 60:
            return f"❌ Прогулянку краще відкласти: висока ймовірність опадів ({max_rain}%)."
        elif avg_temp < 0 or avg_temp > 33:
            return f"⚠️ Не найкомфортніша погода для прогулянок (середня темп.: {avg_temp:.1f}°C)."
        elif max_rain >= 30:
            return (
                f"🌦️ Прогулянка можлива, але можливий невеликий дощ (до {max_rain}%)."
            )
        else:
            return f"✅ Чудовий час для прогулянки! Температура {avg_temp:.1f}°C, без опадів."


class ClothingStrategy(RecommendationStrategy):
    """Стратегія 2: Вибір одягу."""

    def recommend(self, forecast: WeatherForecast) -> str:
        current_temp = forecast.intervals[0].temperature_c

        if current_temp < 5:
            return f"🧥 Теплий зимовий одяг: куртка, шапка, рукавички (зараз {current_temp:.1f}°C)."
        elif current_temp < 15:
            return f"🧥 Демісезонний одяг: легка куртка, худі або пальто ({current_temp:.1f}°C)."
        elif current_temp < 22:
            return f"👕 Комфортний одяг: джинси, сорочка, легкий лонгслів ({current_temp:.1f}°C)."
        else:
            return f"🩳 Легкий літній одяг: футболка, шорти, сонцезахисні окуляри ({current_temp:.1f}°C)."


class PrecipitationStrategy(RecommendationStrategy):
    """Стратегія 3: Підготовка до опадів (парасолька/дощовик)."""

    def recommend(self, forecast: WeatherForecast) -> str:
        intervals = forecast.intervals[:3]
        max_rain = max(i.precipitation_probability for i in intervals)

        if max_rain > 50:
            return f"☂️ Обов'язково візьміть парасольку або водонепроникну куртку (ймовірність {max_rain}%)."
        elif max_rain >= 25:
            return f"🌂 Парасольку варто захопити про всяк випадок (ймовірність {max_rain}%)."
        else:
            return f"☀️ Парасолька не потрібна, опадів не передбачається ({max_rain}%)."


# =====================================================================
# 4. КОМПОНЕНТИ ОТРИМАННЯ ДАНИХ ТА ШАБЛОН DECORATOR
# =====================================================================
class GeocodingClient:
    """Визначення координат населеного пункту через Open-Meteo Geocoding API."""

    URL = "https://geocoding-api.open-meteo.com/v1/search"

    def find_city(self, city_name: str) -> Tuple[float, float, str]:
        params = {"name": city_name, "count": 1, "language": "uk", "format": "json"}
        try:
            resp = requests.get(self.URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Помилка мережі при пошуку міста: {e}")

        results = data.get("results")
        if not results:
            raise ValueError(f"Населений пункт '{city_name}' не знайдено.")

        city_data = results[0]
        return (
            float(city_data["latitude"]),
            float(city_data["longitude"]),
            city_data.get("name", city_name),
        )


class IForecastProvider(ABC):
    @abstractmethod
    def get_forecast(self, latitude: float, longitude: float) -> dict:
        pass


class ForecastProvider(IForecastProvider):
    """Базовий постачальник прогнозу через прямий HTTP-запит."""

    URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        self.http_calls_count = 0

    def get_forecast(self, latitude: float, longitude: float) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation_probability",
            "forecast_days": 1,
            "timezone": "auto",
        }
        try:
            self.http_calls_count += 1
            resp = requests.get(self.URL, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Помилка HTTP-запиту до Open-Meteo: {e}")


class ForecastCacheDecorator(IForecastProvider):
    """Декоратор: кешування прогнозів за координатами з часом життя (TTL)."""

    def __init__(self, provider: IForecastProvider, ttl_seconds: int = 600):
        self.provider = provider
        self.ttl = ttl_seconds
        # Формат: {(round(lat, 3), round(lon, 3)): (data, timestamp)}
        self.cache: Dict[Tuple[float, float], Tuple[dict, float]] = {}

    def get_forecast(self, latitude: float, longitude: float) -> dict:
        key = (round(latitude, 3), round(longitude, 3))
        now = time.time()

        if key in self.cache:
            data, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                print(f"   [Cache HIT] Дані повернуто з пам'яті для координат {key}")
                return data
            else:
                print(f"   [Cache EXPIRED] Термін дії кешу вичерпано. Оновлення...")

        print(f"   [Cache MISS] Звернення до зовнішнього API Open-Meteo...")
        new_data = self.provider.get_forecast(latitude, longitude)
        self.cache[key] = (new_data, now)
        return new_data


# =====================================================================
# 5. СХОВИЩЕ SQLITE (WeatherHistory)
# =====================================================================
class WeatherHistory:
    """Історія прогнозів погоди у SQLite."""

    def __init__(self, db_path: str = "weather_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forecast_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    forecast_time TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    precipitation_probability INTEGER NOT NULL,
                    source TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_forecast(self, forecast: WeatherForecast, limit_intervals: int = 3):
        """Зберігає перші 3 найближчі інтервали отриманого прогнозу."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            rows_to_insert = [
                (
                    forecast.city,
                    forecast.latitude,
                    forecast.longitude,
                    forecast.retrieved_at,
                    interval.time,
                    interval.temperature_c,
                    interval.precipitation_probability,
                    forecast.source,
                )
                for interval in forecast.intervals[:limit_intervals]
            ]
            cursor.executemany(
                """
                INSERT INTO forecast_history 
                (city, latitude, longitude, retrieved_at, forecast_time, temperature_c, precipitation_probability, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                rows_to_insert,
            )
            conn.commit()

    def get_recent(self, limit: int = 6) -> List[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT city, retrieved_at, forecast_time, temperature_c, precipitation_probability, source
                FROM forecast_history
                ORDER BY id DESC LIMIT ?
            """,
                (limit,),
            )
            return cursor.fetchall()

    def get_history_by_city(self, city: str, limit: int = 6) -> List[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT city, retrieved_at, forecast_time, temperature_c, precipitation_probability, source
                FROM forecast_history
                WHERE LOWER(city) = LOWER(?)
                ORDER BY id DESC LIMIT ?
            """,
                (city, limit),
            )
            return cursor.fetchall()


# =====================================================================
# 6. ШАБЛОН FACADE
# =====================================================================
class WeatherFacade:
    """Фасад, що надає єдину точку входу для клієнта."""

    def __init__(self, ttl_seconds: int = 600, db_path: str = "weather_history.db"):
        self.geocoder = GeocodingClient()
        self.base_provider = ForecastProvider()
        self.cached_provider = ForecastCacheDecorator(
            self.base_provider, ttl_seconds=ttl_seconds
        )
        self.history = WeatherHistory(db_path=db_path)

    def get_weather(
        self, city_name: str, strategy: Optional[RecommendationStrategy] = None
    ) -> Tuple[WeatherForecast, str]:
        # 1. Пошук координат
        lat, lon, standard_city = self.geocoder.find_city(city_name)

        # 2. Отримання прогнозу через кешований декоратор
        raw_json = self.cached_provider.get_forecast(lat, lon)

        # 3. Адаптація JSON -> WeatherForecast
        forecast = WeatherAdapter.normalize(standard_city, lat, lon, raw_json)

        # 4. Довготривале збереження в базі даних
        self.history.save_forecast(forecast)

        # 5. Формування рекомендації
        active_strategy = strategy or WalkStrategy()
        recommendation = active_strategy.recommend(forecast)

        return forecast, recommendation


# =====================================================================
# 7. ГОЛОВНЕ КОРИСТУВАЦЬКЕ МЕНЮ (WeatherAssistant)
# =====================================================================
class WeatherAssistant:
    def __init__(self):
        self.facade = WeatherFacade()
        self.strategies = {
            "1": ("Планування прогулянки", WalkStrategy()),
            "2": ("Вибір одягу", ClothingStrategy()),
            "3": ("Підготовка до опадів", PrecipitationStrategy()),
        }

    def run(self):
        while True:
            print("\n" + "=" * 50)
            print("         🌤️  WEATHER ASSISTANT  🌤️")
            print("=" * 50)
            print("1. Отримати прогноз погоди")
            print("2. Переглянути останні записи історії (SQLite)")
            print("3. Переглянути історію за конкретним містом")
            print("4. Вихід")
            choice = input("Оберіть дію (1-4): ").strip()

            if choice == "1":
                city = input("\nВведіть назву міста (наприклад, Lviv, Kyiv): ").strip()
                if not city:
                    continue

                print("\nОберіть алгоритм рекомендацій:")
                for k, v in self.strategies.items():
                    print(f"  {k}. {v[0]}")
                strat_choice = input("Ваш вибір (1-3, за замовчуванням 1): ").strip()
                _, strategy = self.strategies.get(strat_choice, self.strategies["1"])

                try:
                    forecast, recommendation = self.facade.get_weather(city, strategy)
                    self._display_forecast(forecast, recommendation)
                except Exception as e:
                    print(f"\n❌ Помилка: {e}")

            elif choice == "2":
                self._display_history(self.facade.history.get_recent())

            elif choice == "3":
                city = input("Введіть назву міста для пошуку: ").strip()
                self._display_history(self.facade.history.get_history_by_city(city))

            elif choice == "4":
                print("Роботу завершено.")
                break

    def _display_forecast(self, forecast: WeatherForecast, recommendation: str):
        print(
            f"\n📍 Прогноз для: {forecast.city} ({forecast.latitude:.2f}, {forecast.longitude:.2f})"
        )
        print(f"🕒 Час запиту: {forecast.retrieved_at} | Джерело: {forecast.source}")
        print("-" * 50)
        print(f"{'Час прогнозу':<18} | {'Температура':<12} | {'Опади':<10}")
        print("-" * 50)
        for interval in forecast.intervals[:3]:
            print(
                f"{interval.time:<18} | {interval.temperature_c:>5.1f} °C      | {interval.precipitation_probability:>3}%"
            )
        print("-" * 50)
        print("💡 Рекомендація:")
        print(f"   {recommendation}\n")

    def _display_history(self, records: List[tuple]):
        if not records:
            print("\nІсторія порожня.")
            return
        print(
            f"\n{'Місто':<12} | {'Запит':<19} | {'Час прогнозу':<16} | {'Темп.':<6} | {'Опади':<5}"
        )
        print("-" * 70)
        for r in records:
            print(f"{r[0]:<12} | {r[1]:<19} | {r[2]:<16} | {r[3]:>4.1f}°C | {r[4]:>3}%")


if __name__ == "__main__":
    WeatherAssistant().run()
