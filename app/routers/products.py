from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models import Product, User
from app.schemas import ProductOut, ProductUpdate
from app.routers.auth import get_current_user # Защищаем роуты!

router = APIRouter(tags=["Products"])

# 1. Получить список всех товаров пользователя
@router.get("/", response_model=List[ProductOut])
async def get_products(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Показываем товары ТОЛЬКО этого пользователя
    result = await db.execute(
        select(Product)
        .where(Product.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    products = result.scalars().all()
    return products

# 2. Обновить себестоимость товара по SKU
@router.patch("/{sku}", response_model=ProductOut)
async def update_product_costs(
    sku: str,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ищем товар
    result = await db.execute(
        select(Product)
        .where(Product.user_id == current_user.id, Product.sku == sku)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Обновляем только те поля, которые прислали
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return product
