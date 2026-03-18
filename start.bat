@echo off
echo Starting TalentScout Resume Server...
start "TalentScout Resume Server" cmd /c "python scripts\resume_server.py"
echo.
echo TalentScout Resume Server started in a new background window!
echo You can view the parser dashboard at http://localhost:8000
echo.
pause
