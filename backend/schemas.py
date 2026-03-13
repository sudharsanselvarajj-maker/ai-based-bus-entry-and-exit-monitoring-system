from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Log Schemas
class BusLogBase(BaseModel):
    plate_number: str
    event_type: str
    image_path: Optional[str] = None
    gate_id: Optional[str] = "Main_Gate"
    confidence_score: Optional[float] = None

class BusLogCreate(BusLogBase):
    pass

class BusLog(BusLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Vehicle Schemas
class VehicleBase(BaseModel):
    plate_number: str
    bus_nickname: Optional[str] = None
    driver_name: Optional[str] = None

class VehicleCreate(VehicleBase):
    pass

class Vehicle(VehicleBase):
    class Config:
        from_attributes = True
