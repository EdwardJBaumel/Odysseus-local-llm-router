# Bootstrap Odysseus for Auto stack local integration
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$App = Join-Path $Root "odysseus"
$Parent = Split-Path -Parent $Root

# Sibling checkout: prefer local-llm-router folder name, fall back to legacy split-stack
$RouterRepo = $null
foreach ($name in @("local-llm-router", "split-stack")) {
    $candidate = Join-Path $Parent $name
    if (Test-Path (Join-Path $candidate "pyproject.toml")) {
        $RouterRepo = $candidate
        break
    }
}

if (-not $RouterRepo) {
    throw @"
local-llm-router repo not found. Clone it next to this workspace:

  cd $Parent
  git clone https://github.com/EdwardJBaumel/local-llm-router.git local-llm-router

(Legacy folder name split-stack also works.)
"@
}

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

& $Py -m pip install -U pip -q

# Remove deprecated PyPI package name if a prior setup left it behind
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
& $Py -m pip uninstall split-stack -y 2>$null | Out-Null
$ErrorActionPreference = $prevEap

Write-Host "Installing local-llm-router editable from $RouterRepo" -ForegroundColor Cyan
& $Py -m pip install -e "${RouterRepo}[ollama]" -q

# requirements.txt lists local-llm-router for PyPI installs; skip it here — editable above.
$ReqFiltered = Join-Path $env:TEMP "odysseus-requirements-no-router.txt"
Get-Content requirements.txt | Where-Object { $_ -notmatch '^\s*local-llm-router' } | Set-Content $ReqFiltered
& $Py -m pip install -r $ReqFiltered -q

& $Py -m pip install -r requirements-optional.txt -q

$EnvExample = Join-Path $Root "scripts/env.local.example"
if (-not (Test-Path ".env") -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample ".env"
}

$env:ODYSSEUS_SKIP_RUN_HINT = "1"
$env:ODYSSEUS_SKIP_ADMIN_PROMPT = "1"
& $Py setup.py

& $Py -c @"
from src.constants import AUTO_STACK_MODEL_ID
from src.settings import load_settings, save_settings
s = load_settings()
s['default_model'] = AUTO_STACK_MODEL_ID
s['auto_stack_vram_gb'] = 16
s['auto_stack_quant'] = 'qat'
save_settings(s)
print('default_model', s['default_model'])
"@

& $Py (Join-Path $Root "scripts/seed-ollama-endpoint.py")

Write-Host "Setup complete. Run scripts/start-local.ps1"
