# AI-Based Bus Entry and Exit Monitoring System Startup Script
Write-Host "Starting Bus Entry-Exit AI Platform..." -ForegroundColor Cyan

# 1. Start Backend
Write-Host "Launching Backend Server (FastAPI)..." -ForegroundColor Yellow
# Updated to open in a separate visible window so the user can see if errors occur
$BackendArgs = "/c cd backend && .\venv\Scripts\Activate.ps1 && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
Start-Process "cmd.exe" -ArgumentList $BackendArgs -WindowStyle Hidden

# 2. Wait for backend to init
Start-Sleep -Seconds 3

# 3. Open Dashboard
Write-Host "Opening Administrative Dashboard..." -ForegroundColor Green
Start-Process "frontend/index.html"

# 4. Prompt to start AI Pipeline
Write-Host "`nReady! Would you like to start the AI Vision Simulator? (Y/N)" -ForegroundColor White
$choice = Read-Host
if ($choice -eq "Y" -or $choice -eq "y") {
    Write-Host "Launching AI Simulator..." -ForegroundColor Magenta
    cd cv_pipeline
    # Note: Assumes python is in path or venv is used. For simulation, source python is fine.
    .\venv\Scripts\python.exe detector.py
}
