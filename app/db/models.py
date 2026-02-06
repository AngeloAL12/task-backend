from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, default="General")
    deadline = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String, default="media") # alta, media, baja
    is_completed = Column(Boolean, default=False)
    source = Column(String, default="web") # web, telegram, magic
    created_at = Column(DateTime(timezone=True), server_default=func.now())