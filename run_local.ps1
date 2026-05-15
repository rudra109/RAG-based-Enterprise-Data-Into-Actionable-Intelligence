$ErrorActionPreference = "Stop"

Write-Host "Starting EnterpriseIQ Development Stack without Docker..."

# Start Redis (Requires Redis for Windows or WSL)
Write-Host "NOTE: Redis must be running locally on port 6379 for full functionality."

# Frontend
Start-Process powershell -ArgumentList "-NoExit -Command `"cd frontend; npm run dev`"" -WindowStyle Normal

# Backend API
Start-Process powershell -ArgumentList "-NoExit -Command `"cd backend; uvicorn app.main:app --port 8080 --reload`"" -WindowStyle Normal

# ML Services
Start-Process powershell -ArgumentList "-NoExit -Command `"cd ml; uvicorn rag.main:app --port 8001 --reload`"" -WindowStyle Normal
Start-Process powershell -ArgumentList "-NoExit -Command `"cd ml; uvicorn anomaly.main:app --port 8002 --reload`"" -WindowStyle Normal
Start-Process powershell -ArgumentList "-NoExit -Command `"cd ml; uvicorn forecast.main:app --port 8003 --reload`"" -WindowStyle Normal
Start-Process powershell -ArgumentList "-NoExit -Command `"cd ml; uvicorn agent.main:app --port 8004 --reload`"" -WindowStyle Normal
Start-Process powershell -ArgumentList "-NoExit -Command `"cd ml; uvicorn kg.main:app --port 8005 --reload`"" -WindowStyle Normal

Write-Host "All services started in separate windows."
