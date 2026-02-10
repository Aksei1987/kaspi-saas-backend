from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List # <--- Вот этого не хватало в прошлый раз

from app.database import get_db
from app.models import Order, Product, CompanySettings
from app.schemas import DashboardStats, DailyStats
from app.routers.auth import get_current_user
from app.services.importer import sync_kaspi_data

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

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Получаем настройки (налог)
    res_settings = await db.execute(select(CompanySettings).where(CompanySettings.user_id == current_user.id))
    settings = res_settings.scalar_one_or_none()
    tax_percent = settings.tax_percent if settings else 3.0 

    # 2. Период
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 3. Загружаем заказы
    query = (
        select(Order, Product)
        .join(Product, Order.sku == Product.sku, isouter=True)
        .where(
            Order.user_id == current_user.id,
            Order.order_date >= start_date
        )
    )
    result = await db.execute(query)
    rows = result.all()

    # 4. Переменные
    total_revenue = 0.0
    total_profit = 0.0
    total_orders = 0
    products_without_costs = 0
    daily_map = {} 

    # 5. СЧИТАЕМ
    for order, product in rows:
        if order.status in ["Отменен", "Возврат"]:
            continue

        total_orders += 1
        revenue = order.amount
        total_revenue += revenue
        
        # Количество в заказе
        qty = order.quantity if order.quantity and order.quantity > 0 else 1

        total_cogs = 0.0 # Себестоимость товаров
        
        if product:
            # Расходы на ОДНУ штуку
            purchase = product.purchase_price or 0
            log_china = product.logistics_china or 0
            log_inner = product.logistics_inner or 0
            pack = product.packaging_cost or 0
            
            # Умножаем на количество (Закуп * кол-во + Логистика * кол-во...)
            unit_cost = purchase + log_china + log_inner + pack
            total_cogs = unit_cost * qty

            # Комиссия Каспи (% от Цены Продажи)
            comm_percent = product.kaspi_commission or 0
            commission_amount = revenue * (comm_percent / 100)
            
            # Добавляем комиссию к расходам (или можно вычесть отдельно, математика одна)
            total_cogs += commission_amount

            if purchase == 0:
                products_without_costs += 1
        else:
            products_without_costs += 1

        # Налог (% от Цены Продажи)
        tax_amount = revenue * (tax_percent / 100)
        
        # Доставка Каспи (берем из заказа)
        delivery_kaspi = order.delivery_cost_for_seller or 0

        # ФОРМУЛА: Прибыль = Выручка - (Себестоимость*Кол-во + Комиссия) - Налог - ДоставкаКаспи
        profit = revenue - total_cogs - tax_amount - delivery_kaspi
        
        total_profit += profit

        # Группировка по дням
        day_key = order.order_date.date()
        if day_key not in daily_map:
            daily_map[day_key] = {"revenue": 0.0, "profit": 0.0, "count": 0}
        
        daily_map[day_key]["revenue"] += revenue
        daily_map[day_key]["profit"] += profit
        daily_map[day_key]["count"] += 1

    # 6. Итоги
    margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    total_expenses = total_revenue - total_profit
    roi = (total_profit / total_expenses * 100) if total_expenses > 0 else 0

    # 7. График
    chart_data = []
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