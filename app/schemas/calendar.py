from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class CalendarSourceCreate(BaseModel):
    source_url: str
    name: str

class CalendarSourceResponse(CalendarSourceCreate):
    id: int
    user_id: int
    last_synced_at: Optional[datetime]

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    status: str
    new_tasks: int
    updated_tasks: int
