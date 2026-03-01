from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime
from typing import Optional

from app.core.url_safety import validate_calendar_url


class CalendarSourceCreate(BaseModel):
    source_url: str
    name: str

    @field_validator("source_url")
    @classmethod
    def source_url_safe(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("La URL del calendario es obligatoria.")
        validate_calendar_url(v.strip())
        return v.strip()

class CalendarSourceResponse(CalendarSourceCreate):
    id: int
    user_id: int
    last_synced_at: Optional[datetime]
    subject_mapping: Optional[dict] = {}

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    status: str
    new_tasks: int
    updated_tasks: int
    found_subjects: list[str] = []
