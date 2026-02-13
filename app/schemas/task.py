from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

class MagicPayload(BaseModel):
    text: str

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    subject: Optional[str] = Field("General", max_length=50)
    deadline: Optional[datetime] = None
    priority: Optional[Literal["alta", "media", "baja"]] = "media"

class TaskResponse(TaskCreate):
    id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True