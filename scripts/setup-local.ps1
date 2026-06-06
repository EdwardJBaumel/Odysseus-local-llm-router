# Bootstrap Odysseus for Auto stack local integration
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$App = Join-Path $Root "odysseus"
$SplitStack = Join-Path (Split-Path -Parent $Root) "split-stack"

if (-not (Test-Path $App)) {
    throw "Missing odysseus/ clone. See README.md"
}

Set-Location $App

if (-not (Test-Path "venv")) {
    python -m venv venv
}

$Py = Join-Path $App "venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw "venv creation failed"
}

& $Py -m pip install -r requirements.txt -q

$Wheel = Join-Path $SplitStack "dist/split_stack-0.3.1-py3-none-any.whl"
if (Test-Path $Wheel) {
    & $Py -m pip install $Wheel -q
} else {
    Write-Warning "Installing split-stack editable from ../split-stack"
    & $Py -m pip install -e "${SplitStack}[ollama]" -q
}

& $Py -m pip install -r requirements-optional.txt -q

$EnvExample = Join-Path $Root "scripts/env.local.example"
if (-not (Test-Path ".env") -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample ".env"
}

$env:ODYSSEUS_ADMIN_USER = "admin"
$env:ODYSSEUS_ADMIN_PASSWORD = "odysseus-dev-local"
$env:ODYSSEUS_SKIP_RUN_HINT = "1"
& $Py setup.py

$SettingsPath = Join-Path $App "data/settings.json"
$Overlay = @{
    auto_stack_enabled = $true
    auto_stack_vram_gb = 16
    auto_stack_quant = "qat"
}
if (Test-Path $SettingsPath) {
    $s = Get-Content $SettingsPath -Raw | ConvertFrom-Json
    foreach ($k in $Overlay.Keys) {
        $s | Add-Member -NotePropertyName $k -NotePropertyValue $Overlay[$k] -Force
    }
    $s | ConvertTo-Json -Depth 5 | Set-Content $SettingsPath -Encoding utf8
} else {
    $Overlay | ConvertTo-Json | Set-Content $SettingsPath -Encoding utf8
}

& $Py (Join-Path $Root "scripts/seed-ollama-endpoint.py")

Write-Host "Setup complete. Run scripts/start-local.ps1"
