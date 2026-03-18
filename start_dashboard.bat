@echo off
echo Starting TalentScout Dashboard Server...
start "TalentScout Dashboard Server" cmd /c "python scripts\dashboard_server.py"
echo.
echo TalentScout Dashboard Server started in a new background window!
echo You can view the dashboard at http://localhost:8001
echo.
pause
