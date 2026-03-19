@echo off
echo Starting TalentScout Services...
echo.

echo Starting Resume Server (Port 8000)...
start "TalentScout Resume Server" cmd /c "python scripts\resume_server.py"

echo Starting Dashboard Server (Port 8001)...
start "TalentScout Dashboard Server" cmd /c "python scripts\dashboard_server.py"

echo.
echo TalentScout Services started!
echo - Dashboard: http://localhost:8001
echo - Resume Scanner: http://localhost:8000
echo - Crawler Management: http://localhost:8000/manage
echo.
pause
