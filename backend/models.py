from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from database import Base
from datetime import datetime, timezone

class BusLog(Base):
    __tablename__ = "bus_logs"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, index=True)
    event_type = Column(String) # ENTRY or EXIT
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    image_path = Column(String, nullable=True) # Path to saved frame
    gate_id = Column(String, default="Main_Gate")
    confidence_score = Column(Float, nullable=True)

class RegisteredFleet(Base):
    __tablename__ = "registered_fleet"

    plate_number = Column(String, primary_key=True, index=True)
    bus_nickname = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
