from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from typing import List
from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/vehicles",
    tags=["vehicles"]
)

@router.get("/", response_model=List[schemas.Vehicle])
def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    vehicles = db.query(models.RegisteredFleet).offset(skip).limit(limit).all()
    return vehicles

@router.post("/", response_model=schemas.Vehicle)
def register_vehicle(vehicle: schemas.VehicleCreate, db: Session = Depends(get_db)):
    db_vehicle = db.query(models.RegisteredFleet).filter(models.RegisteredFleet.plate_number == vehicle.plate_number).first()
    if db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle already registered")
    
    new_vehicle = models.RegisteredFleet(**vehicle.model_dump())
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

@router.delete("/{plate_number}")
def delete_vehicle(plate_number: str, db: Session = Depends(get_db)):
    db_vehicle = db.query(models.RegisteredFleet).filter(models.RegisteredFleet.plate_number == plate_number).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    db.delete(db_vehicle)
    db.commit()
    return {"message": "Vehicle deleted successfully"}
