from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Task, User
from app.schemas.task import TaskResponse, TaskCreate, TaskUpdate, MagicPayload
from app.services.ai_service import parse_task_with_ai
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/", response_model=List[TaskResponse])
def read_tasks(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return db.query(Task).filter(
        Task.user_id == current_user.id
    ).order_by(Task.deadline).offset(skip).limit(limit).all()


@router.post("/", response_model=TaskResponse)
def create_task(
        task: TaskCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    new_task = Task(
        **task.dict(),
        user_id=current_user.id,
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
    task_data = parse_task_with_ai(payload.text)

    new_task = Task(
        **task_data.dict(),
        user_id=current_user.id,
        source="magic_web"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
        task_id: int,
        task_update: TaskUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no tienes permiso")

    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no tienes permiso")

    db.delete(task)
    db.commit()
    return None
