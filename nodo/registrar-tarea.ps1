# registrar-tarea.ps1 — ALIAS de kynikos.ps1
# Equivale a:  .\nodo\kynikos.ps1 tarea
#
# Este archivo ya no tiene logica propia: todo vive en nodo\kynikos.ps1.
# Se conserva para que los accesos directos y las guias antiguas sigan funcionando.

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "kynikos.ps1") tarea 
exit $LASTEXITCODE
