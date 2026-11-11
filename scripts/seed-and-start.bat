@echo off
setlocal EnableExtensions
REM Seed demo workflows, then start backend + frontend.
REM Usage:
REM   scripts\seed-and-start.bat
REM   set AI_PROVIDER=mock && scripts\seed-and-start.bat
REM   scripts\seed-and-start.bat --no-start

cd /d "%~dp0.."
if errorlevel 1 (
  echo [ERROR] Could not cd to project root from "%~dp0.."
  exit /b 1
)
set "ROOT=%CD%"
set "DO_START=1"
if /I "%~1"=="--no-start" set "DO_START=0"
if /I "%~1"=="/no-start" set "DO_START=0"

if not defined AI_PROVIDER set "AI_PROVIDER=ollama"
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen3:4b"

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [ERROR] .venv not found at "%ROOT%\.venv"
  exit /b 1
)

echo Seeding demo inquiries with AI_PROVIDER=%AI_PROVIDER% ...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\seed_demo.py"
if errorlevel 1 (
  echo [ERROR] seed_demo.py failed
  exit /b 1
)

if "%DO_START%"=="0" (
  echo Seed complete. Skipping start (--no-start).
  exit /b 0
)

echo Seed complete. Starting demo windows ...
call "%ROOT%\scripts\start-demo.bat"
endlocal
exit /b %ERRORLEVEL%