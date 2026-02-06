# app/main.py
from fastapi import FastAPI
from app.routers import tasks
from app.db.database import Base, engine

# Crear tablas al inicio (para desarrollo)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskMaster API", version="1.0.0")

app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])

@app.get("/health")
def health_check():
    return {"status": "ok", "engine": "FastAPI + Gemini Flash"}