from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.database import get_db
from app.db import models
from app.schemas import users as schemas
from app.dependencies import get_current_user, get_current_superadmin
from app.core.security import get_password_hash

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/", response_model=List[schemas.User])
@limiter.limit("60/minute")
def read_users(
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin)
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.get("/me", response_model=schemas.User)
@limiter.limit("60/minute")
def read_user_me(
    request: Request,
    current_user: models.User = Depends(get_current_user)
):
    return current_user

@router.get("/{user_id}", response_model=schemas.User)
@limiter.limit("60/minute")
def read_user(
    request: Request,
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/{user_id}", response_model=schemas.User)
@limiter.limit("10/minute")
def update_user(
        request: Request,
        user_id: int,
        user_update: schemas.UserUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    if current_user.id != user_id and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar a otro usuario"
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user_update.is_superadmin is not None and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes cambiar tus permisos de administrador"
        )

    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            hashed_password = get_password_hash(password)
            user.hashed_password = hashed_password

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def delete_user(
    request: Request,
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    return None
