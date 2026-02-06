from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import Task
from app.schemas.task import TaskResponse, TaskCreate, MagicPayload
from app.services.ai_service import parse_task_with_ai

router = APIRouter()


@router.post("/magic", response_model=TaskResponse)
def create_magic_task(payload: MagicPayload, db: Session = Depends(get_db)):
    # 1. Llamar al servicio de IA
    task_data = parse_task_with_ai(payload.text)

    # 2. Guardar en DB
    new_task = Task(**task_data.dict(), source="magic")
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/", response_model=List[TaskResponse])
def read_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.deadline).all()