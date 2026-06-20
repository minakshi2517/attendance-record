@echo off
echo Starting Attendance App...

set PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe

start "Attendance Backend" /MIN cmd /k "cd /d %~dp0backend && "%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "Attendance Frontend" /MIN cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ========================================
echo  Backend:  http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:5173
echo  Admin:    admin / admin123
echo ========================================
echo Dono CMD windows minimize hongi — band mat karna!
pause
