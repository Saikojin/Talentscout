@echo off
echo ===================================================
echo Starting TalentScout Unified Server (Port 8088)...
echo ===================================================
echo.

start "TalentScout Dashboard Server" cmd /c "python scripts\dashboard_server.py"

echo.
echo TalentScout Services Layout:
echo - Dashboard Server:      http://localhost:8088
echo   * Main Dashboard:      http://localhost:8088
echo   * Profiles & Scoring:  http://localhost:8088/profiles
echo   * Resume Scanner:      http://localhost:8088/scanner
echo   * Crawler Management:  http://localhost:8088/manage
echo.
echo - Standalone Parser:     http://localhost:8085 (Optional / Standalone)
echo - Local LLM Server:      http://localhost:8000 (Started from UI / tailor engine)
echo - Llama Worker Engine:   http://localhost:8080
echo - Resume MCP Server:     http://localhost:3001/mcp
echo ===================================================
echo.
pause
