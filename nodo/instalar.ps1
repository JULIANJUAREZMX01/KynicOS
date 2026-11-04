# Instalador del nodo primario KYNIKOS para Windows (PowerShell).
# Uso:   .\nodo\instalar.ps1
# Deja el bot corriendo con modelo local y Telegram por polling.
# No expone puertos y no cuesta nada por token.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)


function Actualizar-Ruta {
    # Windows no ve programas recien instalados hasta reabrir la terminal.
    # Recargamos el PATH de la maquina y del usuario en ESTA sesion.
    $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$m;$u"
}

function Aviso-Grande($texto) {
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor Red
    Write-Host "   $texto" -ForegroundColor Red
    Write-Host "  ============================================================" -ForegroundColor Red
    Write-Host ""
}

Write-Host "== KYNIKOS · nodo primario (Windows) ==" -ForegroundColor Yellow

# 1. Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "-- instalando Python 3.12" 
    winget install --id Python.Python.3.12 -e --silent
    Actualizar-Ruta
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Aviso-Grande "INSTALACION INCOMPLETA: cierra PowerShell, abre una nueva y repite el script"
        exit 1
    }
}

# 2. Ollama
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "-- instalando Ollama (modelo local, sin costo por token)"
    winget install --id Ollama.Ollama -e --silent
    Actualizar-Ruta
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        Aviso-Grande "INSTALACION INCOMPLETA: cierra PowerShell, abre una nueva y repite el script"
        exit 1
    }
}

# 3. Modelo: 7B es el óptimo para 16 GB sin GPU dedicada (unos 5 tok/s)
$modelo = if ($env:KYNIKOS_MODELO) { $env:KYNIKOS_MODELO } else { "qwen2.5:7b" }
Write-Host "-- descargando modelo $modelo (una sola vez, unos 4.7 GB)"
ollama pull $modelo

# 4. Entorno de Python
Write-Host "-- entorno de Python"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -q --upgrade pip
.\.venv\Scripts\python.exe -m pip install -q -r requirements-bot.txt

# 5. .env: el token se pide sin mostrarse en pantalla
if (-not (Test-Path .env)) {
    $seguro = Read-Host "Pega el token de @kynicOS_robot (no se mostrará)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)

    $palabra = Read-Host "Palabra del primer paso (KYNIKOS_PALABRA_1)"
    @"
TELEGRAM_TOKEN=$token
TELEGRAM_USER_ID=8247886073
PERSONA=kynikos
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=$modelo
OLLAMA_NUM_CTX=4096
MAX_TOKENS_SALIDA=768
TIMEOUT_LLM=300
KYNIKOS_PALABRA_1=$palabra
KYNIKOS_ESTADO_DIR=.kynikos
"@ | Set-Content -Path .env -Encoding UTF8
    Write-Host "-- .env creado"
}

# 5b. Verificacion dura: sin .venv no hay nodo
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Aviso-Grande "FALLO: no se creo el entorno .venv. Revisa los errores de arriba."
    exit 1
}

# 6. Comprobar el bot y que NO haya webhook que estorbe al polling
$env:TELEGRAM_TOKEN = (Get-Content .env | Where-Object { $_ -like "TELEGRAM_TOKEN=*" }) -replace "TELEGRAM_TOKEN=", ""
.\.venv\Scripts\python.exe cli\kynikos.py telegram

Write-Host ""
Write-Host "Listo. Para arrancar el nodo:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe cli\kynikos.py run"
