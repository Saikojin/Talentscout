@echo off
echo Stopping TalentScout services...

rem Kill process on port 8088 (Dashboard Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8088 ^| findstr LISTENING') do (
    echo Killing Dashboard Server on port 8088 PID: %%a
    taskkill /F /T /PID %%a
)

rem Kill process on port 8085 (Standalone Resume Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8085 ^| findstr LISTENING') do (
    echo Killing Standalone Resume Server on port 8085 PID: %%a
    taskkill /F /T /PID %%a
)

rem Kill process on port 8000 (LLM Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing LLM Server on port 8000 PID: %%a
    taskkill /F /T /PID %%a
)

rem Kill process on port 8080 (LlamaServer Worker)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do (
    echo Killing Llama Worker on port 8080 PID: %%a
    taskkill /F /T /PID %%a
)

rem Kill process on port 3001 (MCP Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3001 ^| findstr LISTENING') do (
    echo Killing MCP Server on port 3001 PID: %%a
    taskkill /F /T /PID %%a
)

echo.
echo TalentScout Services stopped!
pause
