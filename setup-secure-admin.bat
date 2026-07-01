@echo off
cd /d "%~dp0backend"

set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if not exist "%PY%" set PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
if not exist "%PY%" set PY=python

if not exist ".env" (
  echo Creating secure .env ...
  "%PY%" scripts\generate_env.py
)

echo Applying admin credentials to database ...
"%PY%" scripts\reset_admin.py

echo.
echo Done. Open ADMIN_CREDENTIALS.local.txt for login details.
pause
