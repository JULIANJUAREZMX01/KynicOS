# automatico.ps1 — ALIAS de kynikos.ps1
#
# Tenia 152 lineas propias que duplicaban el orquestador: otra copia de la
# logica de requisitos, puerto, dependencias y validacion. Dos copias divergen
# siempre, y la que se queda vieja es la que se ejecuta.
#
# Ahora solo delega. La logica vive unicamente en nodo\kynikos.ps1.
& (Join-Path $PSScriptRoot "kynikos.ps1") @args
exit $LASTEXITCODE
