@echo off
echo Opening backend + frontend in separate windows...
start "Interview Sarathi - Backend" cmd /k "%~dp0start-backend.bat"
timeout /t 3 /nobreak >nul
start "Interview Sarathi - Frontend" cmd /k "%~dp0start-frontend.bat"
echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:3000
echo Open the FRONTEND URL in your browser.
