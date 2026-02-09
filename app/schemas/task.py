from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MagicPayload(BaseModel):
    text: str

class TaskCreate(BaseModel):
    title: str
    subject: Optional[str] = "General"
    deadline: Optional[datetime] = None
    priority: Optional[str] = "media"

class TaskResponse(TaskCreate):
    id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True