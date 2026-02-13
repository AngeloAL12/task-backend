from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, BigInteger
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

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(BigInteger, index=True)

    title = Column(String, index=True)
    subject = Column(String)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String, default="media")
    is_completed = Column(Boolean, default=False)
    source = Column(String)
    external_uid = Column(String, index=True, nullable=True) # Unique ID from iCal
    calendar_source_id = Column(Integer, nullable=True) # FK to calendar_sources


    created_at = Column(DateTime, server_default=func.now())

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(BigInteger, index=True)

    name = Column(String)
    schedule_text = Column(String)

class CalendarSource(Base):
    __tablename__ = "calendar_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True) # Linking to User.id (not telegram_id, though user has telegram_id)
    source_url = Column(String)
    name = Column(String)
    last_synced_at = Column(DateTime, nullable=True)