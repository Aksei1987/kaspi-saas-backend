import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Order, Product
from datetime import datetime

async def sync_kaspi_data(csv_url: str, user_id: int, db: AsyncSession):
    # 1. Скачиваем данные через Pandas
    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        return {"error": f"Не удалось скачать файл: {str(e)}"}

    # 2. Переименуем колонки для удобства (Русский -> English)
    # Каспи может менять названия, поэтому используем .get() или проверяем
    column_map = {
        '№ заказа': 'kaspi_id',
        'Артикул': 'sku',
        'Сумма': 'amount',
        'Статус': 'status',
        'Дата поступления заказа': 'order_date',
        'Стоимость доставки для продавца': 'delivery_cost',
        'Название товара в Kaspi Магазине': 'product_name'
        'Количество': 'quantity' # <--- ДОБАВИЛИ
    }
    df = df.rename(columns=column_map)
    
    # Оставляем только нужные колонки
    needed_cols = list(column_map.values())
    # Фильтруем, если каких-то колонок нет в файле - не страшно, pandas просто проигнорирует
    df = df[df.columns.intersection(needed_cols)]

    imported_count = 0
    
    # 3. Проходимся по каждой строке
    for index, row in df.iterrows():
        # --- Очистка данных ---
        
if not existing_order:
            # Получаем количество, если пусто - ставим 1
            qty_val = 1
            try:
                qty_val = int(row.get('quantity', 1))
            except:
                qty_val = 1

            new_order = Order(
                user_id=user_id,
                kaspi_id=kaspi_order_id,
                sku=sku_clean,
                product_name=str(row.get('product_name', '')),
                amount=float(str(row['amount']).replace(',', '.').replace(' ', '')),
                status=str(row['status']),
                order_date=date_obj,
                quantity=qty_val, # <--- ЗАПИСЫВАЕМ В БАЗУ
                delivery_cost_for_seller=float(str(row.get('delivery_cost', 0)).replace(',', '.').replace(' ', '') or 0)
            )
            db.add(new_order)
            imported_count += 1

        # Чистим SKU (иногда там бывают пробелы)
        sku_clean = str(row['sku']).strip()
        
        # --- Работа с Товаром (Product) ---
        # Проверяем, есть ли такой товар у нас в базе?
        stmt = select(Product).where(Product.user_id == user_id, Product.sku == sku_clean)
        result = await db.execute(stmt)
        existing_product = result.scalar_one_or_none()

        # Если товара нет - создаем его (чтобы потом заполнить себестоимость)
        if not existing_product:
            new_product = Product(
                user_id=user_id,
                sku=sku_clean,
                name=str(row.get('product_name', 'Unknown')),
                purchase_price=0.0 # Пока 0, пользователь потом заполнит
            )
            db.add(new_product)
            # Надо закоммитить, чтобы товар сразу появился для следующих проверок
            await db.commit() 

        # --- Работа с Заказом (Order) ---
        # Проверяем, не загружали ли мы этот заказ ранее? (по ID заказа)
        kaspi_order_id = str(row['kaspi_id'])
        stmt_order = select(Order).where(Order.user_id == user_id, Order.kaspi_id == kaspi_order_id)
        res_order = await db.execute(stmt_order)
        existing_order = res_order.scalar_one_or_none()

        if not existing_order:
            new_order = Order(
                user_id=user_id,
                kaspi_id=kaspi_order_id,
                sku=sku_clean,
                product_name=str(row.get('product_name', '')),
                amount=float(str(row['amount']).replace(',', '.').replace(' ', '')), # Убираем пробелы в цене
                status=str(row['status']),
                order_date=date_obj,
                delivery_cost_for_seller=float(str(row.get('delivery_cost', 0)).replace(',', '.').replace(' ', '') or 0)
            )
            db.add(new_order)
            imported_count += 1
    
    await db.commit()
    return {"status": "success", "imported": imported_count}
