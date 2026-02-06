from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Lo que el usuario manda en el "Input Mágico"
class MagicPayload(BaseModel):
    text: str

# Lo que recibimos para crear manual (Clásico)
class TaskCreate(BaseModel):
    title: str
    subject: Optional[str] = "General"
    deadline: Optional[datetime] = None
    priority: Optional[str] = "media"

# Lo que devolvemos al frontend
class TaskResponse(TaskCreate):
    id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True