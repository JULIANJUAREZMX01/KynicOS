# ARRANQUE TODO EN UNO — nodo KYNIKOS en Windows
#
# Copia este archivo completo en PowerShell y ejecútalo. Hace todo:
# comprueba requisitos, trae el repositorio, instala lo que falta,
# configura el .env y deja el nodo listo para arrancar.
#
# Uso:
#   .\arranque-todo-en-uno.ps1                 (instala y luego arranca)
#   .\arranque-todo-en-uno.ps1 -SoloInstalar    (instala y no arranca)
#
# No pide permisos de administrador. No instala nada de pago.

param(
    [switch]$SoloInstalar
)

$ErrorActionPreference = "Stop"

function Paso($texto) { Write-Host ""; Write-Host "== $texto" -ForegroundColor Yellow }
function Bien($texto) { Write-Host "   $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "   $texto" -ForegroundColor Cyan }
function Fallo($texto) { Write-Host "   $texto" -ForegroundColor Red }

Paso "KYNIKOS · arranque completo"
Write-Host "   Este script no instala nada de pago." -ForegroundColor DarkGray

# ---------------------------------------------------------------- 1. Git
Paso "1/5 · Git"
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Aviso "Git no está instalado. Instalando con winget..."
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    Fallo "Cierra esta ventana, abre PowerShell de nuevo y vuelve a ejecutar el script."
    exit 0
}
Bien "Git disponible."

# ---------------------------------------------------------------- 2. Repositorio
Paso "2/5 · Repositorio"
$destino = Join-Path $HOME "Documents\KynicOS"
if (Test-Path (Join-Path $destino ".git")) {
    Aviso "Ya existe en $destino. Actualizando..."
    Push-Location $destino
    git pull --ff-only
    Pop-Location
    Bien "Repositorio actualizado."
} else {
    Aviso "Clonando en $destino ..."
    New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
    git clone https://github.com/JULIANJUAREZMX01/KynicOS.git $destino
    Bien "Repositorio listo."
}

Set-Location $destino

# ---------------------------------------------------------------- 3. Instalador
Paso "3/5 · Instalador del nodo"
$instalador = Join-Path $destino "nodo\instalar.ps1"
if (-not (Test-Path $instalador)) {
    Fallo "No se encontró nodo\instalar.ps1. Revisa que el repositorio se clonó completo."
    exit 1
}

# La política de ejecución se relaja solo para esta ventana, no para el sistema.
try {
    Set-ExecutionPolicy -Scope Process -Bypass -Force
} catch {
    Aviso "No se pudo ajustar la política de ejecución; si falla, ejecútalo a mano."
}

& $instalador
if ($LASTEXITCODE -ne 0) {
    Fallo "El instalador terminó con error. Lee el mensaje de arriba: casi siempre es Python u Ollama recién instalados."
    Aviso "Cierra esta ventana, abre PowerShell de nuevo y repite el script."
    exit 1
}

# ---------------------------------------------------------------- 4. Revisión
Paso "4/5 · Revisión de la configuración"
$envFile = Join-Path $destino ".env"
if (-not (Test-Path $envFile)) {
    Fallo "No se creó el archivo .env. Vuelve a ejecutar el instalador."
    exit 1
}

$contenido = Get-Content $envFile
$faltantes = @()
foreach ($clave in @("TELEGRAM_TOKEN", "TELEGRAM_USER_ID", "KYNIKOS_PALABRA_1")) {
    $linea = $contenido | Where-Object { $_ -like "$clave=*" }
    $valor = if ($linea) { ($linea -split "=", 2)[1].Trim() } else { "" }
    if ([string]::IsNullOrWhiteSpace($valor)) { $faltantes += $clave }
}

if ($faltantes.Count -gt 0) {
    Fallo ("Faltan valores en .env: " + ($faltantes -join ", "))
    Aviso "Edítalos con:  notepad .env"
    exit 1
}
Bien "Token, usuario y palabra del primer paso están puestos."

$python = Join-Path $destino ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Fallo "No existe el entorno de Python (.venv). El instalador no terminó bien."
    exit 1
}

$env:TELEGRAM_TOKEN = (($contenido | Where-Object { $_ -like "TELEGRAM_TOKEN=*" }) -split "=", 2)[1].Trim()
$clave1 = (($contenido | Where-Object { $_ -like "KYNIKOS_PALABRA_1=*" }) -split "=", 2)[1].Trim()

Paso "5/5 · Comprobación del bot en Telegram"
$respuesta = & $python "cli\kynikos.py" telegram 2>&1
$respuesta | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }

# ---------------------------------------------------------------- Fin
Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Bien "Nodo instalado y configurado."
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para arrancarlo ahora:" -ForegroundColor Yellow
Write-Host "  cd `"$destino`""
Write-Host "  .\.venv\Scripts\python.exe cli\kynikos.py run"
Write-Host ""
Write-Host "Para probarlo: escribe cualquier cosa a @kynicOS_robot en Telegram."
Write-Host "La palabra del primer paso activa la verificación de doble paso."
Write-Host ""
Aviso "Deja la ventana abierta mientras quieras que el bot esté vivo."

if (-not $SoloInstalar) {
    Write-Host ""
    Write-Host "Arrancando el nodo. Ctrl+C para detenerlo." -ForegroundColor Yellow
    & $python "cli\kynikos.py" run
}
