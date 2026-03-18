@echo off
echo Stopping TalentScout services...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process listening on port 8000 ^(PID: %%a^)
    taskkill /F /PID %%a
)

echo.
echo TalentScout Resume Server stopped!
pause
