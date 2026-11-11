@echo off
setlocal EnableExtensions
REM Start backend + frontend. Default AI_PROVIDER=ollama (ignores leaked mock env).
REM Usage:
REM   scripts\start-demo.bat
REM   scripts\start-demo.bat mock

cd /d "%~dp0.."
if errorlevel 1 (
  echo [ERROR] Could not cd to project root from "%~dp0.."
  exit /b 1
)
set "ROOT=%CD%"

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [ERROR] .venv not found at "%ROOT%\.venv"
  exit /b 1
)
if not exist "%ROOT%\frontend\package.json" (
  echo [ERROR] frontend\package.json not found under "%ROOT%"
  exit /b 1
)

REM Force demo defaults: ollama unless first arg is mock
if /I "%~1"=="mock" (
  set "AI_PROVIDER=mock"
) else (
  set "AI_PROVIDER=ollama"
)
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen3:4b"
if not defined OLLAMA_BASE_URL set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
if not defined NEXT_PUBLIC_API_BASE set "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000"
set "OLLAMA_ALLOW_MOCK_FALLBACK=false"

echo.
echo === AI Inquiry Processing Agent - start demo ===
echo ROOT=%ROOT%
echo AI_PROVIDER=%AI_PROVIDER%
echo OLLAMA_MODEL=%OLLAMA_MODEL%
echo OLLAMA_BASE_URL=%OLLAMA_BASE_URL%
echo NEXT_PUBLIC_API_BASE=%NEXT_PUBLIC_API_BASE%
echo.
echo Tip: offline/CI style: scripts\start-demo.bat mock
echo.

start "AIPA-backend" cmd /k call "%ROOT%\scripts\_run-backend.bat"
start "AIPA-frontend" cmd /k call "%ROOT%\scripts\_run-frontend.bat"

echo Opened two windows: AIPA-backend and AIPA-frontend
echo UI:  http://127.0.0.1:3000
echo API: http://127.0.0.1:8000/docs
echo Provider: http://127.0.0.1:8000/api/v1/provider
echo Stop with: scripts\stop-demo.bat
endlocal
exit /b 0