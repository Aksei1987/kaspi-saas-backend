from pydantic import BaseModel, EmailStr
from typing import Optional, List  # <--- ДОБАВИЛ List
from datetime import date

# Базовая схема токена (то, что мы отдадим фронтенду после логина)
class Token(BaseModel):
    access_token: str
    token_type: str

# Схема для создания пользователя (регистрация)
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Схема для отображения пользователя (без пароля!)
class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True

# Схема для обновления себестоимости
class ProductUpdate(BaseModel):
    purchase_price: Optional[float] = None  # Закуп
    logistics_china: Optional[float] = None # Доставка Китай
    logistics_inner: Optional[float] = None # Фулфилмент
    other_expenses: Optional[float] = None  # Упаковка/прочее
    kaspi_commission: Optional[float] = None # Комиссия (%)

# Схема для показа товара
class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    purchase_price: float
    logistics_china: float
    logistics_inner: float
    other_expenses: float
    kaspi_commission: float

    class Config:
        from_attributes = True

# Статистика за один день (для графика)
class DailyStats(BaseModel):
    date: date
    revenue: float  # Выручка
    profit: float   # Прибыль
    orders_count: int

# Общая сводка (карточки сверху)
class DashboardStats(BaseModel):
    total_revenue: float
    total_profit: float
    total_orders: int
    margin_percent: float     # Маржинальность %
    roi_percent: float        # ROI %
    
    # Для графика
    chart_data: List[DailyStats]
    
    # Предупреждение: сколько товаров без себестоимости (чтобы ты знал, что статистика врет)
    products_without_costs: int