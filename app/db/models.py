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

    created_at = Column(DateTime, server_default=func.now())

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)

    telegram_id = Column(BigInteger, index=True)

    name = Column(String)
    schedule_text = Column(String)