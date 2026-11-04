# CENTRO.ps1 — lanzador del centro de comando del nodo KYNIKOS
#
#   .\nodo\CENTRO.ps1
#
# Busca el python del entorno del nodo y abre el menu. No instala nada ni
# modifica nada: solo lanza nodo\centro.py, que hace el resto.

$ErrorActionPreference = "Stop"
$nodo = $PSScriptRoot
$repo = Split-Path $nodo -Parent

$candidatos = @(
    (Join-Path $nodo ".venv\Scripts\python.exe"),
    (Join-Path $repo ".venv\Scripts\python.exe")
)
$python = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) { $python = "python" }

$centro = Join-Path $nodo "centro.py"
if (-not (Test-Path $centro)) {
    Write-Host "No encuentro nodo\centro.py" -ForegroundColor Red
    exit 1
}

Push-Location $repo
try {
    & $python $centro
} finally {
    Pop-Location
}
exit $LASTEXITCODE
