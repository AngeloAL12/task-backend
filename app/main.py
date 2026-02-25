# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from app.routers import tasks
from app.db.database import Base, engine
from app.bot import create_bot_app
from app.routers import auth, users
from app.routers import calendars # <--- Importar el nuevo router
from app.services.reminders import check_and_send_reminders
from asyncio import create_task
import asyncio



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    bot_app = create_bot_app()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    print("🤖 Bot de Telegram conectado y escuchando dentro de FastAPI")

    reminder_task = create_task(check_and_send_reminders(bot_app))

    yield

    print("🛑 Deteniendo Bot de Telegram...")
    reminder_task.cancel()
    try:
        await reminder_task
    except asyncio.CancelledError:
        pass

    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(
    title="TaskMaster AI",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todo (ajustar en prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(calendars.router)

app.include_router(api_v1_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "engine": "FastAPI + Gemini + Telegram Bot"}