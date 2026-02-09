from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(Integer, index=True)

    title = Column(String, index=True)
    subject = Column(String)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String, default="media")
    is_completed = Column(Boolean, default=False)
    source = Column(String)