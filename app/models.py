from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    settings = relationship("CompanySettings", back_populates="owner", uselist=False)
    products = relationship("Product", back_populates="owner")
    orders = relationship("Order", back_populates="owner")  # <--- ДОБАВИЛ ЭТУ СТРОКУ

class CompanySettings(Base):
    __tablename__ = "company_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String, nullable=True)
    tax_percent = Column(Float, default=3.0)
    google_sheet_url = Column(String, nullable=True)

    owner = relationship("User", back_populates="settings")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sku = Column(String, index=True)
    name = Column(String)
    
    purchase_price = Column(Float, default=0.0)
    logistics_china = Column(Float, default=0.0)
    logistics_inner = Column(Float, default=0.0)
    other_expenses = Column(Float, default=0.0)
    kaspi_commission = Column(Float, default=0.0)

    owner = relationship("User", back_populates="products")

# --- НОВАЯ ТАБЛИЦА ЗАКАЗОВ ---
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    kaspi_id = Column(String, index=True) # Номер заказа (чтобы не дублировать)
    sku = Column(String, index=True)      # Артикул
    product_name = Column(String)         # Название товара
    amount = Column(Float)                # Сумма продажи
    status = Column(String)               # Статус (Архив/Доставлен)
    
    order_date = Column(DateTime)         # Дата заказа
    delivery_cost_for_seller = Column(Float, default=0.0) # Доставка продавца

    owner = relationship("User", back_populates="orders")