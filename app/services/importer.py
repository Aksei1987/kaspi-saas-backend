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

    # 2. Переименуем колонки для удобства
    # ВАЖНО: В конце каждой строки должна быть запятая!
    column_map = {
        '№ заказа': 'kaspi_id',
        'Артикул': 'sku',
        'Сумма': 'amount',
        'Статус': 'status',
        'Дата поступления заказа': 'order_date',
        'Стоимость доставки для продавца': 'delivery_cost',
        'Название товара в Kaspi Магазине': 'product_name',
        'Количество': 'quantity' 
    }
    df = df.rename(columns=column_map)
    
    # Оставляем только нужные колонки (пересечение)
    needed_cols = list(column_map.values())
    df = df[df.columns.intersection(needed_cols)]

    imported_count = 0
    
    # 3. Проходимся по каждой строке
    for index, row in df.iterrows():
        # --- Очистка данных ---
        
        # Парсим дату
        try:
            # Каспи обычно дает дату как "29.03.2025" или "29.03.25 14:00"
            date_str = str(row['order_date']).split(' ')[0] # Берем только дату
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        except:
            date_obj = datetime.now()

        # Чистим SKU
        sku_clean = str(row['sku']).strip()
        
        # --- Работа с Товаром (Product) ---
        stmt = select(Product).where(Product.user_id == user_id, Product.sku == sku_clean)
        result = await db.execute(stmt)
        existing_product = result.scalar_one_or_none()

        if not existing_product:
            new_product = Product(
                user_id=user_id,
                sku=sku_clean,
                name=str(row.get('product_name', 'Unknown')),
                purchase_price=0.0
            )
            db.add(new_product)
            await db.commit() 

        # --- Работа с Заказом (Order) ---
        kaspi_order_id = str(row['kaspi_id'])
        stmt_order = select(Order).where(Order.user_id == user_id, Order.kaspi_id == kaspi_order_id)
        res_order = await db.execute(stmt_order)
        existing_order = res_order.scalar_one_or_none()

        if not existing_order:
            # Получаем количество (если пусто или ошибка, ставим 1)
            qty_val = 1
            try:
                raw_qty = row.get('quantity', 1)
                qty_val = int(float(str(raw_qty).replace(',', '.'))) # защита от "1,0"
            except:
                qty_val = 1
            
            # Чистим цену и доставку от пробелов
            try:
                amount_val = float(str(row['amount']).replace(',', '.').replace(' ', '').replace('\xa0', ''))
            except:
                amount_val = 0.0

            try:
                delivery_val = float(str(row.get('delivery_cost', 0)).replace(',', '.').replace(' ', '').replace('\xa0', ''))
            except:
                delivery_val = 0.0

            new_order = Order(
                user_id=user_id,
                kaspi_id=kaspi_order_id,
                sku=sku_clean,
                product_name=str(row.get('product_name', '')),
                amount=amount_val,
                status=str(row['status']),
                order_date=date_obj,
                quantity=qty_val,
                delivery_cost_for_seller=delivery_val
            )
            db.add(new_order)
            imported_count += 1
    
    await db.commit()
    return {"status": "success", "imported": imported_count}