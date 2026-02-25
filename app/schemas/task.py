from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, Literal

def calculate_dynamic_priority(deadline: Optional[datetime], current_priority: str = "media") -> str:
    if not deadline:
        return current_priority
        
    now = datetime.now()
    if deadline.tzinfo is not None:
        now = now.astimezone()
    
    deadline_date = deadline.date()
    today = now.date()
    
    delta_days = (deadline_date - today).days

    if delta_days <= 1:
        return "alta"
    elif delta_days in (2, 3):
        return "media"
    else:
        return "baja"


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

    @model_validator(mode="after")
    def compute_dynamic_priority(self) -> "TaskResponse":
        self.priority = calculate_dynamic_priority(self.deadline, self.priority)
        return self

    class Config:
        from_attributes = True