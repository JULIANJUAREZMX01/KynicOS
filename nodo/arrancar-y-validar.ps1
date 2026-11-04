# KYNIKOS · arrancar y validar
#
# Copia y pega este archivo en PowerShell. Hace todo y al final te dice
# si el nodo quedó vivo, con prueba real contra Telegram.
#
#   .\nodo\arrancar-y-validar.ps1
#
# No pide administrador. No instala nada de pago.

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Titulo($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Yellow }
function Bien($t) { Write-Host "   OK   $t" -ForegroundColor Green }
function Mal($t) { Write-Host "   FALLO $t" -ForegroundColor Red }
function Info($t) { Write-Host "   $t" -ForegroundColor Cyan }

Titulo "KYNIKOS · arrancar y validar"

# ---------------------------------------------------------------- 1. Limpieza
Titulo "1/6 · Limpiar tareas viejas"
$tarea = Get-ScheduledTask -TaskName "KYNIKOS nodo" -ErrorAction SilentlyContinue
if ($tarea) {
    Unregister-ScheduledTask -TaskName "KYNIKOS nodo" -Confirm:$false
    Bien "Tarea anterior eliminada (apuntaba a un entorno que no existía)."
} else {
    Bien "No había tareas viejas."
}

# ---------------------------------------------------------------- 2. Repositorio
Titulo "2/6 · Actualizar el repositorio"
if (-not (Test-Path (Join-Path $repo ".git"))) {
    Mal "Esta carpeta no es el repositorio. Clónalo primero:"
    Info 'git clone https://github.com/JULIANJUAREZMX01/KynicOS.git $HOME\Documents\KynicOS'
    exit 1
}
$ErrorActionPreference = "Continue"   # git escribe progreso en stderr y no es un error
git pull --ff-only 2>&1 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
$ErrorActionPreference = "Stop"
Bien "Repositorio al día."

# ---------------------------------------------------------------- 3. Requisitos
Titulo "3/6 · Comprobar requisitos"
$faltan = @()
foreach ($p in @("git", "python", "ollama")) {
    if (-not (Get-Command $p -ErrorAction SilentlyContinue)) { $faltan += $p }
}
if ($faltan.Count -gt 0) {
    Mal ("Falta: " + ($faltan -join ", "))
    Info "Instálalos y vuelve a ejecutar este script:"
    if ($faltan -contains "git")    { Info "  winget install --id Git.Git -e --source winget" }
    if ($faltan -contains "python") { Info "  winget install --id Python.Python.3.12 -e" }
    if ($faltan -contains "ollama") { Info "  winget install --id Ollama.Ollama -e" }
    Info "Después cierra esta ventana y abre PowerShell de nuevo."
    exit 1
}
Bien "git, python y ollama disponibles."

# ---------------------------------------------------------------- 4. Instalación
Titulo "4/6 · Entorno y configuración"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$envFile = Join-Path $repo ".env"

if ((Test-Path $python) -and (Test-Path $envFile)) {
    Bien "El entorno ya existe; no hace falta reinstalar."
} else {
    Info "Instalando. Te pedirá el token del bot (no se ve al pegarlo) y la palabra del primer paso."
    try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction Stop } catch { }
    & (Join-Path $PSScriptRoot "instalar.ps1")
    if ($LASTEXITCODE -ne 0) {
        Mal "La instalación no terminó. Lee el mensaje rojo de arriba."
        exit 1
    }
    if (-not (Test-Path $python)) { Mal "No se creó el entorno .venv."; exit 1 }
    Bien "Entorno y .env listos."
}

$lineas = Get-Content $envFile
$token = (($lineas | Where-Object { $_ -like "TELEGRAM_TOKEN=*" }) -split "=", 2)[1].Trim()
if ([string]::IsNullOrWhiteSpace($token)) { Mal "TELEGRAM_TOKEN vacío en .env"; exit 1 }
$env:TELEGRAM_TOKEN = $token
Bien "Token cargado desde .env."

# ---------------------------------------------------------------- 5. Arranque
Titulo "5/6 · Arrancar el nodo en segundo plano"
$yaCorre = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
           Where-Object { $_.CommandLine -like "*kynikos.py*run*" }
if ($yaCorre) {
    Bien "Ya había un nodo corriendo (PID $($yaCorre[0].ProcessId)). No se duplica."
} else {
    $log = Join-Path $repo "kynikos.log"
    $err = Join-Path $repo "kynikos.err.log"
    $proc = Start-Process -FilePath $python `
        -ArgumentList "cli\kynikos.py", "run" `
        -WorkingDirectory $repo `
        -RedirectStandardOutput $log `
        -RedirectStandardError $err `
        -WindowStyle Hidden -PassThru
    Info "Lanzado con PID $($proc.Id). Esperando 12 segundos..."
    Start-Sleep -Seconds 12

    if ($proc.HasExited) {
        Mal "El proceso murió al arrancar. Esto es lo que dijo:"
        if (Test-Path $err) { Get-Content $err -Tail 20 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray } }
        if (Test-Path $log) { Get-Content $log -Tail 10 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray } }
        exit 1
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $repo ".kynikos") | Out-Null
    $proc.Id | Set-Content (Join-Path $repo ".kynikos\nodo.pid")
    Bien "Proceso vivo (PID $($proc.Id))."
}

# ---------------------------------------------------------------- 6. Validación real
Titulo "6/6 · Validar contra Telegram"
# Si el nodo está haciendo polling, Telegram rechaza una segunda consulta
# con error 409. Esa es la prueba de que alguien está escuchando de verdad.
$vivo = $false
try {
    Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getUpdates?timeout=0&limit=1" -TimeoutSec 20 | Out-Null
} catch {
    $codigo = $null
    try { $codigo = $_.Exception.Response.StatusCode.value__ } catch { }
    if ($codigo -eq 409) { $vivo = $true }
}

if ($vivo) {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Bien "VALIDADO: el nodo está escuchando a Telegram."
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Prueba final a mano: escribe /estado a @kynicOS_robot" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Registro de actividad: $repo\kynikos.log"
    Write-Host "  Detenerlo:             Stop-Process -Id (Get-Content .\.kynikos\nodo.pid)"
    Write-Host "  Arranque automatico:   .\nodo\registrar-tarea.ps1"
    exit 0
}

Mal "El proceso está vivo, pero Telegram no reporta que alguien escuche."
Info "Suele ser el token: revisa que sea el de @kynicOS_robot dentro de .env"
Info "Log: $repo\kynikos.err.log"
exit 1
