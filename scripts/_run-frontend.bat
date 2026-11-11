@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "ROOT=%CD%"
if not defined NEXT_PUBLIC_API_BASE set "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000"
cd /d "%ROOT%\frontend"
echo Starting Next.js on http://127.0.0.1:3000 ...
echo NEXT_PUBLIC_API_BASE=%NEXT_PUBLIC_API_BASE%
npm run dev
endlocal