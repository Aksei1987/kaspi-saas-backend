from fastapi import FastAPI
from app.config import settings
from app.routers import auth, analytics, products  # <--- Добавили products

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(analytics.router, prefix="/api/v1/analytics")
app.include_router(products.router, prefix="/api/v1/products") # <--- Подключили

@app.get("/")
def read_root():
    return {"Status": "Active", "Version": "1.0.0"}