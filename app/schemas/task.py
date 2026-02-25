from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal

class MagicPayload(BaseModel):
    text: str

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    subject: Optional[str] = Field("General", max_length=50)
    deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    priority: Optional[Literal["alta", "media", "baja"]] = "media"

    @field_validator("priority", mode="before")
    @classmethod
    def lowercase_priority(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    subject: Optional[str] = Field(None, max_length=50)
    deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    priority: Optional[Literal["alta", "media", "baja"]] = None
    is_completed: Optional[bool] = None

    @field_validator("priority", mode="before")
    @classmethod
    def lowercase_priority(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

class TaskResponse(TaskCreate):
    id: int
    is_completed: bool
    created_at: datetime
    sent_reminders: list[int] = []

    class Config:
        from_attributes = True