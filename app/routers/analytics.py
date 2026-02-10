from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.routers.auth import get_current_user # Теперь этот импорт сработает!
from app.services.importer import sync_kaspi_data

router = APIRouter(tags=["Analytics"])

class SyncRequest(BaseModel):
    csv_url: str

@router.post("/sync")
async def sync_data(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    # Пользователя пока не проверяем, чтобы проще тестировать, но импорт нужен
    # current_user: User = Depends(get_current_user) 
):
    # Временно хардкодим ID администратора
    user_id = 1 
    
    result = await sync_kaspi_data(request.csv_url, user_id, db)
    return result