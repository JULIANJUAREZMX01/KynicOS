# CENTRO.ps1 — ALIAS de nodo\kynikos.ps1 (ADR-031)
#
# Tenia 31 lineas de logica propia que duplicaban al orquestador. Dos copias
# divergen y la que se ejecuta acaba siendo la vieja. La logica vive solo en
# nodo\kynikos.ps1.
#
# Uso recomendado: .\nodo\kynikos.ps1 centro
& (Join-Path $PSScriptRoot "kynikos.ps1") centro
exit $LASTEXITCODE
