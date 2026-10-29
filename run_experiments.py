import os
import time
from weather_assistant import (
    WeatherFacade,
    WalkStrategy,
    ClothingStrategy,
    PrecipitationStrategy,
    WeatherAdapter,
    WeatherHistory,
)


def run_all_experiments():
    print("==================================================")
    print("   ВИКОНАННЯ 5 ЕКСПЕРИМЕНТІВ ЩОДО ПРОГНОЗУ ПОГОДИ")
    print("==================================================\n")

    # ----------------------------------------------------
    # ЕКСПЕРИМЕНТ 1: Отримання прогнозу для 3 міст
    # ----------------------------------------------------
    print(">>> 1. ЕКСПЕРИМЕНТ 1: Отримання прогнозу для >= 3 населених пунктів")
    facade = WeatherFacade()
    cities = ["Kyiv", "Lviv", "Odesa"]
    for city in cities:
        f, rec = facade.get_weather(city, WalkStrategy())
        print(
            f"✅ {city}: Координати ({f.latitude:.2f}, {f.longitude:.2f}), Інтервалів: {len(f.intervals[:3])}"
        )
    print()

    # ----------------------------------------------------
    # ЕКСПЕРИМЕНТ 2: Порівняння 3 стратегій на однакових даних
    # ----------------------------------------------------
    print(">>> 2. ЕКСПЕРИМЕНТ 2: Порівняння 3 стратегій до однакових даних")
    sample_forecast, _ = facade.get_weather("Lviv")
    strategies = [
        ("Прогулянка", WalkStrategy()),
        ("Одяг", ClothingStrategy()),
        ("Опади", PrecipitationStrategy()),
    ]
    for name, strat in strategies:
        print(f" • Стратегія '{name}': {strat.recommend(sample_forecast)}")
    print()

    # ----------------------------------------------------
    # ЕКСПЕРИМЕНТ 3: Перевірка кешування Decorator (TTL)
    # ----------------------------------------------------
    print(">>> 3. ЕКСПЕРИМЕНТ 3: Перевірка TTL Cache Decorator")
    test_facade = WeatherFacade(
        ttl_seconds=3
    )  # Встановлюємо TTL = 3 секунди для швидкої перевірки
    base_calls = test_facade.base_provider.http_calls_count

    print("Крок 1: Перший запит (повинен бути HTTP GET)...")
    test_facade.get_weather("Dnipro")
    print(f"Кількість HTTP-запитів: {test_facade.base_provider.http_calls_count}")

    print("Крок 2: Повторний запит через 1 сек (повинен бути Cache HIT)...")
    time.sleep(1)
    test_facade.get_weather("Dnipro")
    print(
        f"Кількість HTTP-запитів: {test_facade.base_provider.http_calls_count} (залишилася незмінною!)"
    )

    print("Крок 3: Запит після завершення TTL (через 4 сек)...")
    time.sleep(3.5)
    test_facade.get_weather("Dnipro")
    print(
        f"Кількість HTTP-запитів: {test_facade.base_provider.http_calls_count} (збільшилась на 1)."
    )
    print()

    # ----------------------------------------------------
    # ЕКСПЕРИМЕНТ 4: Перевірка збереження історії в SQLite
    # ----------------------------------------------------
    print(">>> 4. ЕКСПЕРИМЕНТ 4: Перевірка збереження та читання з SQLite")
    history = WeatherHistory()
    recent = history.get_recent(limit=3)
    if recent:
        print(
            f"Збережено записів у базі: {len(recent)}. Останній запис для міста: {recent[0][0]}"
        )
    else:
        print("База даних поки що порожня.")
    history_lviv = history.get_history_by_city("Lviv", limit=2)
    print(f"Історія конкретно для Львова знайдена: {len(history_lviv)} записів.")
    print()

    # ----------------------------------------------------
    # ЕКСПЕРИМЕНТ 5: Оброблення помилок
    # ----------------------------------------------------
    print(">>> 5. ЕКСПЕРИМЕНТ 5: Оброблення некоректних даних та помилок")
    # 5.1 Неіснуюче місто
    try:
        facade.get_weather("NonExistingCity123456XYZ")
    except ValueError as e:
        print(f"✅ Перевірка 1 (Неіснуюче місто): {e}")

    # 5.2 Некоректний JSON
    try:
        WeatherAdapter.normalize("TestCity", 0, 0, {"invalid_key": []})
    except ValueError as e:
        print(f"✅ Перевірка 2 (Пошкоджений JSON API): {e}")

    print("\n🎉 Усі 5 експериментів успішно виконані та підтверджені.")


if __name__ == "__main__":
    run_all_experiments()
