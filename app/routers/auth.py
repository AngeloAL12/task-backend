from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models import User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    ALGORITHM,
    SECRET_KEY,
)
from app.core.config import settings
from app.schemas.auth import UserCreate, Token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
def register_user(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if db_user:
        raise HTTPException(status_code=400, detail="Este email ya está registrado.")

    hashed_pwd = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    refresh_token = create_refresh_token(data={"sub": new_user.email})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    # Mensaje genérico para no revelar si el email existe o no
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
def refresh_access_token(
    request: Request,
    refresh_token: str,
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de refresco inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": user.email})

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
