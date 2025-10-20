# main.py
from notification.notification_router import notification_router
from user.routes.user_router import user_router
from auth.routes.auth_router import auth_router

from core.database import get_client
from core.config import get_settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends
from pathlib import Path
from dotenv import load_dotenv
from perfil.routes.perfil_router import perfil_router
from cv.routes.cv_router import cv_router
from metricas.routes.metricas_router import metricas_router


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


app = FastAPI()


app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(notification_router, prefix="/api")
app.include_router(perfil_router, prefix="/api")   # ← NEW
app.include_router(cv_router, prefix="/api")
app.include_router(metricas_router, prefix="/api")


cfg = get_settings()
origins = cfg.BACKEND_CORS_ORIGINS if cfg.BACKEND_CORS_ORIGINS else [
    "http://localhost:3000"]
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def ensure_indexes():
    db = get_client().get_default_database()
    try:
        await db.command("ping")
        await db["users"].create_index("email", unique=True)
        print("Mongo OK (startup) + índices listos")
    except Exception as e:
        # No bloquees el arranque si la DB no está — logueá y seguí
        print(f"Mongo NO disponible (startup): {e} — sigo sin bloquear")


@app.get("/health")
async def health():
    return {"status": "ok", "env": cfg.ENVIRONMENT, "db": cfg.MONGO_DATABASE}
