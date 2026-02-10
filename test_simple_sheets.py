import pandas as pd
import io

# ВСТАВЬ СЮДА СВОЮ ССЫЛКУ ИЗ ШАГА 1
# (Она должна быть в кавычках)
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQf7WRG0Mxv4_08Wy9LY6a3L4dCuC3z8_V4AALuZET4qAUEsEW5AWuIulzOJ8fvct_1-3dauRZ8XKNq/pub?output=csv"

try:
    print("Скачиваю данные...")

    # Pandas сам идет по ссылке и превращает данные в таблицу
    df = pd.read_csv(csv_url)

    print("--- УСПЕХ! ---")
    print(f"Найдено строк: {len(df)}")
    print("Первые 5 строк таблицы:")
    print(df.head())

    # Проверим, какие есть колонки
    print("\nСписок колонок:", list(df.columns))

except Exception as e:
    print(f"Ошибка: {e}")
    print("Совет: Проверь, что в конце ссылки написано output=csv")
