# ARRANQUE TODO EN UNO - solo un atajo
#
# Antes repetia toda la instalacion por su cuenta y se quedo atras: pedia el
# token, lo validaba mal y sobrescribia un .env que ya funcionaba. Ahora
# delega en arrancar-y-validar.ps1, que es el unico camino mantenido.

param(
    [switch]$SoloInstalar
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $PSScriptRoot "arrancar-y-validar.ps1"))) {
    Write-Host "   Falta nodo\arrancar-y-validar.ps1. Ejecuta: git pull" -ForegroundColor Red
    exit 1
}

if ($SoloInstalar) {
    & (Join-Path $PSScriptRoot "instalar.ps1")
} else {
    & (Join-Path $PSScriptRoot "arrancar-y-validar.ps1")
}
