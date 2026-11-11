# Start backend + frontend. Default AI_PROVIDER=ollama (ignores leaked mock env).
# Usage:
#   .\scripts\start-demo.ps1
#   .\scripts\start-demo.ps1 mock

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error ".venv not found at $Root\.venv - create with: py -m venv .venv"
}

if ($args.Count -gt 0 -and $args[0] -eq "mock") {
    $env:AI_PROVIDER = "mock"
} else {
    $env:AI_PROVIDER = "ollama"
}
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen3:4b" }
if (-not $env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL = "http://127.0.0.1:11434" }
if (-not $env:OLLAMA_ALLOW_MOCK_FALLBACK) { $env:OLLAMA_ALLOW_MOCK_FALLBACK = "false" }
if (-not $env:OLLAMA_TIMEOUT_SECONDS) { $env:OLLAMA_TIMEOUT_SECONDS = "300" }
if (-not $env:NEXT_PUBLIC_API_BASE) { $env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000" }

Write-Host "=== AI Inquiry Processing Agent - start demo ==="
Write-Host "ROOT=$Root"
Write-Host "AI_PROVIDER=$($env:AI_PROVIDER)  OLLAMA_MODEL=$($env:OLLAMA_MODEL)"
Write-Host "OLLAMA_ALLOW_MOCK_FALLBACK=$($env:OLLAMA_ALLOW_MOCK_FALLBACK)"
Write-Host "NEXT_PUBLIC_API_BASE=$($env:NEXT_PUBLIC_API_BASE)"
Write-Host "Tip: .\scripts\start-demo.ps1 mock for offline/CI style"

$backendCmd = @"
Set-Location '$Root\backend'
& '$Root\.venv\Scripts\Activate.ps1'
`$env:AI_PROVIDER='$($env:AI_PROVIDER)'
`$env:OLLAMA_MODEL='$($env:OLLAMA_MODEL)'
`$env:OLLAMA_BASE_URL='$($env:OLLAMA_BASE_URL)'
`$env:OLLAMA_ALLOW_MOCK_FALLBACK='$($env:OLLAMA_ALLOW_MOCK_FALLBACK)'
`$env:OLLAMA_TIMEOUT_SECONDS='$($env:OLLAMA_TIMEOUT_SECONDS)'
Write-Host 'Starting uvicorn on http://127.0.0.1:8000 ...'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"@

$frontendCmd = @"
Set-Location '$Root\frontend'
`$env:NEXT_PUBLIC_API_BASE='$($env:NEXT_PUBLIC_API_BASE)'
Write-Host 'Starting Next.js on http://127.0.0.1:3000 ...'
npm run dev
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCmd) -WindowStyle Normal
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCmd) -WindowStyle Normal

Write-Host "Opened two windows."
Write-Host "UI:  http://127.0.0.1:3000"
Write-Host "API: http://127.0.0.1:8000/docs"
Write-Host "Provider: http://127.0.0.1:8000/api/v1/provider"
Write-Host "Stop with: .\scripts\stop-demo.ps1"
