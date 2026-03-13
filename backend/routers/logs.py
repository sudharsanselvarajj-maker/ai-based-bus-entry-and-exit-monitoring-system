from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models as models
import schemas as schemas

router = APIRouter(
    prefix="/logs",
    tags=["logs"]
)

@router.get("/", response_model=List[schemas.BusLog])
def get_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(models.BusLog).order_by(models.BusLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs

@router.post("/", response_model=schemas.BusLog)
def create_log(log: schemas.BusLogCreate, db: Session = Depends(get_db)):
    db_log = models.BusLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # Simple stats for dashboard
    total_entries = db.query(models.BusLog).filter(models.BusLog.event_type == "ENTRY").count()
    total_exits = db.query(models.BusLog).filter(models.BusLog.event_type == "EXIT").count()
    
    # Logic for "Buses Inside" (Simplified: total entry - total exit)
    # In a real system, we'd track specific vehicle states
    buses_inside = total_entries - total_exits
    if buses_inside < 0: buses_inside = 0

    return {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "buses_inside": buses_inside
    }
