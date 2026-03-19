@echo off
echo Stopping TalentScout services...

rem Kill process on port 8000 (Resume Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process listening on port 8000 PID: %%a
    taskkill /F /T /PID %%a
)

rem Kill process on port 8001 (Dashboard Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do (
    echo Killing process listening on port 8001 PID: %%a
    taskkill /F /T /PID %%a
)

echo.
echo TalentScout Services stopped!
pause
