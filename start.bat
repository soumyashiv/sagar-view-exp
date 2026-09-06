@echo off
REM SAGAR-VIEW — Quick Start Script (Windows)
REM Run from: sagarview\

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  SAGAR-VIEW — Indian Ocean Visualization  ║
echo  ║  SIH 2026 · Problem 26067                ║
echo  ╚══════════════════════════════════════════╝
echo.

REM Step 1: Generate demo data
echo [1/3] Generating demo NetCDF...
cd backend
python scripts\generate_demo_data.py
if errorlevel 1 (
    echo ERROR: Failed to generate demo data.
    pause
    exit /b 1
)
echo      Done. Validating...
python scripts\validate_netcdf.py data\demo\indian_ocean_demo.nc
echo.

REM Step 2: Start backend in a new window
echo [2/3] Starting FastAPI backend on :8000 ...
start "SAGAR-VIEW Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak > nul

REM Step 3: Start frontend in a new window
echo [3/3] Starting Next.js frontend on :3000 ...
cd ..\frontend
start "SAGAR-VIEW Frontend" cmd /k "npm run dev"

echo.
echo  ✓  Backend:  http://localhost:8000/docs
echo  ✓  Frontend: http://localhost:3000
echo.
echo  Press any key to exit this launcher (servers keep running)
pause > nul
