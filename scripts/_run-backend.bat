@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "ROOT=%CD%"
if not defined AI_PROVIDER set "AI_PROVIDER=ollama"
if not defined OLLAMA_MODEL set "OLLAMA_MODEL=qwen3:4b"
if not defined OLLAMA_BASE_URL set "OLLAMA_BASE_URL=http://127.0.0.1:11434"
if not defined OLLAMA_ALLOW_MOCK_FALLBACK set "OLLAMA_ALLOW_MOCK_FALLBACK=false"
if not defined OLLAMA_TIMEOUT_SECONDS set "OLLAMA_TIMEOUT_SECONDS=300"
cd /d "%ROOT%\backend"
call "%ROOT%\.venv\Scripts\activate.bat"
echo Starting uvicorn on http://127.0.0.1:8000 ...
echo AI_PROVIDER=%AI_PROVIDER% OLLAMA_MODEL=%OLLAMA_MODEL% OLLAMA_BASE_URL=%OLLAMA_BASE_URL%
echo OLLAMA_ALLOW_MOCK_FALLBACK=%OLLAMA_ALLOW_MOCK_FALLBACK%
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
endlocal