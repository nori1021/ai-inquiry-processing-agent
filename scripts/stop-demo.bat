@echo off
setlocal EnableExtensions
REM Gently stop listeners on demo ports 8000 (API) and 3000 (UI).

echo Stopping processes listening on ports 8000 and 3000 ...

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-demo.ps1"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  echo Done.
) else (
  echo stop-demo finished with code %RC%
)
endlocal
exit /b %RC%