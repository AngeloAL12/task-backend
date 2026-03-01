from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models import CalendarSource, User
from app.schemas.calendar import CalendarSourceCreate, CalendarSourceResponse, SyncResponse
from app.dependencies import get_current_user
from app.services.sync_service import SyncService

router = APIRouter(
    prefix="/calendars",
    tags=["Calendars"]
)

@router.post("/", response_model=CalendarSourceResponse)
@limiter.limit("5/minute")
def create_calendar_source(
        request: Request,
        source: CalendarSourceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="Tu usuario web no está vinculado a una cuenta de Telegram aún."
        )

    db_source = CalendarSource(
        user_id=current_user.id,
        source_url=source.source_url,
        name=source.name
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    
    SyncService.sync_calendar(db_source.id, db)
    
    return db_source

@router.get("/", response_model=List[CalendarSourceResponse])
@limiter.limit("60/minute")
def read_calendar_sources(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return db.query(CalendarSource).filter(
        CalendarSource.user_id == current_user.id
    ).offset(skip).limit(limit).all()

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def delete_calendar_source(
        request: Request,
        source_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    source = db.query(CalendarSource).filter(
        CalendarSource.id == source_id,
        CalendarSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Calendario no encontrado")
        
    db.delete(source)
    db.commit()
    return None

@router.post("/{source_id}/sync", response_model=SyncResponse)
@limiter.limit("10/minute")
def sync_calendar(
        request: Request,
        source_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Verify ownership
    source = db.query(CalendarSource).filter(
        CalendarSource.id == source_id,
        CalendarSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Calendario no encontrado o no tienes permiso")

    result = SyncService.sync_calendar(source_id, db)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result


@router.patch("/{source_id}/mapping", response_model=SyncResponse)
@limiter.limit("20/minute")
def update_mapping(
        request: Request,
        source_id: int,
        mapping: Dict[str, str],
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    source = db.query(CalendarSource).filter(
        CalendarSource.id == source_id,
        CalendarSource.user_id == current_user.id
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail="Calendario no encontrado")

    current_mapping = dict(source.subject_mapping or {})

    current_mapping.update(mapping)

    source.subject_mapping = current_mapping

    db.commit()

    result = SyncService.sync_calendar(source_id, db)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
