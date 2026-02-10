from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

SECRET_KEY = settings.SECRET_KEY if hasattr(settings, "SECRET_KEY") else "TU_SECRETO_SUPER_SECRETO_CAMBIALO_EN_PROD"


def verify_password(plain_password, hashed_password):
    """Revisa si la contraseña escrita coincide con el hash guardado."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Convierte 'hola123' en '$2b$12$EixZaYVK1fsdf...'"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera el JWT firmado por nosotros."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)  # Token dura 30 mins por defecto

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt