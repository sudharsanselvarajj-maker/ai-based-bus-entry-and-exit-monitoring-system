from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base
import models as models
from routers import logs, vehicles

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-Based Bus Entry and Exit Monitoring System API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(vehicles.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SmartGate API is running"}
