from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
import os
import sys

# Add the current directory to sys.path to resolve 'database', 'models', etc.
# in both standalone execution and as a package, helping IDEs clear "red dots".
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

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

# Mount captures folder to serve images
captures_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "captures")
if not os.path.exists(captures_path):
    os.makedirs(captures_path)
app.mount("/captures", StaticFiles(directory=captures_path), name="captures")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SmartGate API is running"}
