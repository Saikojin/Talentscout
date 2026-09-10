@echo off
echo Starting TalentScout Unified Server (Port 8088)...
echo.

start "TalentScout Dashboard Server" cmd /c "python scripts\dashboard_server.py"

echo.
echo TalentScout Server started!
echo - Dashboard: http://localhost:8088
echo - Profiles & Scoring: http://localhost:8088/profiles
echo - Resume Scanner: http://localhost:8088/scanner
echo - Crawler Management: http://localhost:8088/manage
echo.
echo Note: Local LLM can be started directly from the Dashboard UI or via tailor engine.
echo.
pause
