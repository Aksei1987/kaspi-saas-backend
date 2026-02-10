from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <--- ИМПОРТ 1
from app.config import settings
from app.routers import auth, analytics, products

app = FastAPI(title=settings.PROJECT_NAME)

# --- НАСТРОЙКА CORS (НОВОЕ) ---
# Это разрешает запросы с любого сайта (для разработки удобно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене тут будет адрес твоего сайта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(analytics.router, prefix="/api/v1/analytics")
app.include_router(products.router, prefix="/api/v1/products")

@app.get("/")
def read_root():
    return {"Status": "Active", "Version": "1.0.0"}