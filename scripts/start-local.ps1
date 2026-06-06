# Start Odysseus on http://127.0.0.1:7000
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$App = Join-Path $Root "odysseus"
Set-Location $App
if (-not (Test-Path "venv")) {
    Write-Error "Run scripts/setup-local.ps1 first"
}
Write-Host "Odysseus → http://127.0.0.1:7000 (admin / odysseus-dev-local)" -ForegroundColor Cyan
& .\venv\Scripts\python -m uvicorn app:app --host 127.0.0.1 --port 7000
