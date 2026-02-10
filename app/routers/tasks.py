from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Task, User
from app.schemas.task import TaskResponse, TaskCreate, MagicPayload
from app.services.ai_service import parse_task_with_ai
from app.dependencies import get_current_user  # <--- El Guardia de Seguridad

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/", response_model=List[TaskResponse])
def read_tasks(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # <--- Solo usuarios logueados
):
    # ESTRATEGIA: "El Truco de Magia" 🎩
    # Si el usuario Web tiene un telegram_id vinculado en la tabla 'users',
    # le mostramos sus tareas de Telegram.

    if current_user.telegram_id:
        return db.query(Task).filter(
            Task.telegram_id == current_user.telegram_id
        ).order_by(Task.deadline).offset(skip).limit(limit).all()

    # Si no tiene telegram_id, por ahora devolvemos lista vacía
    # (o podrías filtrar por un nuevo campo user_id si decides migrar)
    return []

@router.post("/", response_model=TaskResponse)
def create_task(
        task: TaskCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="Tu usuario web no está vinculado a una cuenta de Telegram aún."
        )

    new_task = Task(
        **task.dict(),
        telegram_id=current_user.telegram_id,  # <--- Asignamos al dueño
        source="web"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.post("/magic", response_model=TaskResponse)
def create_magic_task(
        payload: MagicPayload,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="Tu usuario web no está vinculado a una cuenta de Telegram aún."
        )

    task_data = parse_task_with_ai(payload.text)

    new_task = Task(
        **task_data.dict(),
        telegram_id=current_user.telegram_id,  # <--- La clave
        source="magic_web"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Buscamos la tarea Y verificamos que sea del usuario
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.telegram_id == current_user.telegram_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no tienes permiso")

    db.delete(task)
    db.commit()
    return None