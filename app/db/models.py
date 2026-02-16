from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, BigInteger, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)

    telegram_id = Column(BigInteger, nullable=True, unique=True)
    is_superadmin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    tasks = relationship("Task", back_populates="user")
    subjects = relationship("Subject", back_populates="user")
    calendar_sources = relationship("CalendarSource", back_populates="user")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    title = Column(String, index=True)
    start_date = Column(DateTime, nullable=True)
    subject = Column(String)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String, default="media")
    is_completed = Column(Boolean, default=False)
    source = Column(String)
    external_uid = Column(String, index=True, nullable=True) # Unique ID from iCal
    calendar_source_id = Column(Integer, ForeignKey("calendar_sources.id"), nullable=True)

    user = relationship("User", back_populates="tasks")
    calendar_source = relationship("CalendarSource", back_populates="tasks")

    created_at = Column(DateTime, server_default=func.now())

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    name = Column(String)
    schedule_text = Column(String)

    user = relationship("User", back_populates="subjects")

class CalendarSource(Base):
    __tablename__ = "calendar_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    source_url = Column(String)
    name = Column(String)
    subject_mapping = Column(JSON, default={})
    last_synced_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="calendar_sources")
    tasks = relationship("Task", back_populates="calendar_source")