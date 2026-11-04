# arranque-todo-en-uno.ps1 — ALIAS de kynikos.ps1
#
#   .\nodo\arranque-todo-en-uno.ps1                 instala (si hace falta) y arranca
#   .\nodo\arranque-todo-en-uno.ps1 -SoloInstalar    solo prepara, sin arrancar

param([switch]$SoloInstalar)

$ErrorActionPreference = "Stop"
if ($SoloInstalar) {
    & (Join-Path $PSScriptRoot "kynikos.ps1") instalar
} else {
    & (Join-Path $PSScriptRoot "kynikos.ps1") auto
}
exit $LASTEXITCODE
