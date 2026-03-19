# AI-Based Bus Entry and Exit Monitoring System Startup Script
Write-Host "Starting Bus Entry-Exit AI Platform..." -ForegroundColor Cyan

# Function to kill process on a specific port
function Clear-Port($port) {
    try {
        $procId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
        if ($procId) {
            Write-Host "Cleaning up existing process on port $port (PID: $procId)..." -ForegroundColor Magenta
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    } catch {}
}

# 1. Pre-start cleanup
Clear-Port 8000

# 2. Start Backend
Write-Host "Launching Backend Server (FastAPI)..." -ForegroundColor Yellow
$BackendArgs = "/c cd backend && .\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
$backendProc = Start-Process "cmd.exe" -ArgumentList $BackendArgs -PassThru -WindowStyle Minimized

# 3. Wait for backend to init (increased wait for slower systems)
Write-Host "Waiting for backend services..." -ForegroundColor White
Start-Sleep -Seconds 6

# 4. Open Dashboard
Write-Host "Opening Administrative Dashboard..." -ForegroundColor Green
Start-Process "frontend/index.html"

# 5. Start AI Pipeline (Automated with 5sec timeout)
Write-Host "`nLaunching AI Vision Simulator in 5 seconds... (Press Ctrl+C to skip)" -ForegroundColor Gray
Start-Sleep -Seconds 5

try {
    Write-Host "Launching AI Simulator..." -ForegroundColor Magenta
    Set-Location -Path "cv_pipeline"
    .\venv\Scripts\python.exe detector.py
} finally {
    Write-Host "`nTerminating all services..." -ForegroundColor Yellow
    if ($backendProc) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
    Clear-Port 8000
}
