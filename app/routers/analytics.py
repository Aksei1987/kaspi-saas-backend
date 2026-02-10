from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import cast, Date
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Order, Product, CompanySettings
from app.schemas import DashboardStats, DailyStats
from app.routers.auth import get_current_user
from app.services.importer import sync_kaspi_data
from pydantic import BaseModel

router = APIRouter(tags=["Analytics"])

class SyncRequest(BaseModel):
    csv_url: str

@router.post("/sync")
async def sync_data(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await sync_kaspi_data(request.csv_url, current_user.id, db)

# --- НОВЫЙ ENDPOINT ДЛЯ ДАШБОРДА ---
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = 30,  # За сколько дней считать (по умолчанию 30)
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Получаем настройки компании (чтобы узнать налог)
    res_settings = await db.execute(select(CompanySettings).where(CompanySettings.user_id == current_user.id))
    settings = res_settings.scalar_one_or_none()
    tax_percent = settings.tax_percent if settings else 3.0 # Если настроек нет, берем 3%

    # 2. Определяем даты
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 3. Загружаем заказы за этот период + сразу подгружаем товары (join)
    # Мы берем только те заказы, которые НЕ отменены (статус != Cancelled, тут надо смотреть как Каспи пишет)
    # Пока берем все, кроме "Отменен" (проверь в CSV точное слово, обычно "Отменен" или "Возврат")
    query = (
        select(Order, Product)
        .join(Product, Order.sku == Product.sku, isouter=True) # isouter=True значит "даже если товара нет в базе"
        .where(
            Order.user_id == current_user.id,
            Order.order_date >= start_date
        )
    )
    result = await db.execute(query)
    rows = result.all() # Список пар (Order, Product)

    # 4. Переменные для итогов
    total_revenue = 0.0
    total_profit = 0.0
    total_orders = 0
    products_without_costs = 0
    
    # Словарь для группировки по дням (для графика)
    daily_map = {} 

# 5. ГЛАВНЫЙ ЦИКЛ РАСЧЕТА
    for order, product in rows:
        # Пропускаем отмененные
        if order.status in ["Отменен", "Возврат"]:
            continue

        total_orders += 1
        revenue = order.amount
        total_revenue += revenue
        
        # Получаем количество товара в заказе (если вдруг 0, считаем как 1)
        qty = order.quantity if order.quantity and order.quantity > 0 else 1

        # Считаем расходы (Себестоимость)
        total_cogs = 0.0 # Cost of Goods Sold (Себестоимость проданных товаров)
        
        if product:
            # 1. Расходы на единицу (Закуп + Логистика + Упаковка)
            purchase = product.purchase_price or 0
            log_china = product.logistics_china or 0
            log_inner = product.logistics_inner or 0
            pack = product.packaging_cost or 0
            
            unit_cost = purchase + log_china + log_inner + pack
            
            # Умножаем на количество в заказе!
            total_cogs = unit_cost * qty

            # 2. Комиссия Каспи (Считается от Цены продажи)
            # Если в товаре указан %, например 11
            comm_percent = product.kaspi_commission or 0
            commission_amount = revenue * (comm_percent / 100)
            
            # Добавляем комиссию к расходам
            total_cogs += commission_amount

            # Проверка для статистики
            if purchase == 0:
                products_without_costs += 1
        else:
            products_without_costs += 1

        # 3. Налог (Считается от Цены продажи)
        tax_amount = revenue * (tax_percent / 100)
        
        # 4. Доставка Каспи (берется из заказа, она обычно за весь заказ)
        delivery_kaspi = order.delivery_cost_for_seller or 0

        # --- ИТОГОВАЯ ФОРМУЛА ЧИСТОЙ ПРИБЫЛИ ---
        # Прибыль = Выручка - (Себестоимость*Кол-во + Комиссия) - Налог - ДоставкаКаспи
        profit = revenue - total_cogs - tax_amount - delivery_kaspi
        
        total_profit += profit

        # Записываем в статистику дня
        day_key = order.order_date.date()
        if day_key not in daily_map:
            daily_map[day_key] = {"revenue": 0.0, "profit": 0.0, "count": 0}
        
        daily_map[day_key]["revenue"] += revenue
        daily_map[day_key]["profit"] += profit
        daily_map[day_key]["count"] += 1
        
    # 6. Финальные расчеты процентов
    margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    # ROI = Прибыль / Расходы * 100. Расходы = Выручка - Прибыль
    total_expenses = total_revenue - total_profit
    roi = (total_profit / total_expenses * 100) if total_expenses > 0 else 0

    # 7. Формируем список для графика
    chart_data = []
    # Сортируем дни
    for day in sorted(daily_map.keys()):
        stats = daily_map[day]
        chart_data.append(DailyStats(
            date=day,
            revenue=round(stats["revenue"], 2),
            profit=round(stats["profit"], 2),
            orders_count=stats["count"]
        ))

    return DashboardStats(
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2),
        total_orders=total_orders,
        margin_percent=round(margin, 2),
        roi_percent=round(roi, 2),
        chart_data=chart_data,
        products_without_costs=products_without_costs
    )