@echo off
echo Stopping TalentScout Dashboard services...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do (
    echo Killing process listening on port 8001 ^(PID: %%a^)
    taskkill /F /PID %%a
)

echo.
echo TalentScout Dashboard Server stopped!
pause
