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

function Actualizar-Ruta {
    # Recarga el PATH de esta ventana para ver lo recien instalado sin cerrarla.
    $maquina = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $usuario = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$maquina;$usuario"
    # Ollama se instala por usuario y a veces no entra al PATH hasta reiniciar.
    $ollamaDir = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
    if ((Test-Path $ollamaDir) -and ($env:Path -notlike "*$ollamaDir*")) { $env:Path += ";$ollamaDir" }
}

$paquetes = [ordered]@{
    git    = "Git.Git"
    python = "Python.Python.3.12"
    ollama = "Ollama.Ollama"
}

$faltan = @($paquetes.Keys | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })

if ($faltan.Count -gt 0) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Mal ("Falta: " + ($faltan -join ", ") + " y esta PC no tiene winget para instalarlos solo.")
        Info "Instálalos a mano desde: git-scm.com, python.org y ollama.com, y vuelve a correr este script."
        exit 1
    }
    foreach ($nombre in $faltan) {
        Info "Instalando $nombre ($($paquetes[$nombre]))... puede tardar unos minutos."
        & winget install --id $paquetes[$nombre] -e --silent --accept-package-agreements --accept-source-agreements 2>&1 |
            ForEach-Object { if ($_ -match "Successfully|Correctamente|instalad|Found|Encontrado") { Info "  $_" } }
    }
    Actualizar-Ruta
    $siguen = @($paquetes.Keys | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })
    if ($siguen.Count -gt 0) {
        Mal ("Se instalaron, pero esta ventana aún no los ve: " + ($siguen -join ", "))
        Info "Cierra esta ventana, abre PowerShell de nuevo y ejecuta el mismo comando. Ya no hará falta instalar nada."
        exit 1
    }
}
Bien "git, python y ollama disponibles."

# ---------------------------------------------------------------- 4. Instalación
Titulo "4/6 · Entorno y configuración"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$envFile = Join-Path $repo ".env"

function Test-Entorno {
    # No basta con que exista .venv: importa lo que el nodo necesita de verdad.
    if (-not (Test-Path $python)) { return $false }
    & $python -c "import telegram, loguru, httpx" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Path $python)) {
    Info "Creando el entorno e instalando dependencias."
    Info "Te pedirá el token del bot (no se ve al pegarlo) y la palabra del primer paso."
    try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction Stop } catch { }
    & (Join-Path $PSScriptRoot "instalar.ps1")
    if ($LASTEXITCODE -ne 0) {
        Mal "La instalación no terminó. Lee el mensaje rojo de arriba."
        exit 1
    }
}

if (-not (Test-Entorno)) {
    Info "El entorno existe pero le faltan dependencias. Reparando (tarda un poco)..."
    foreach ($req in @("requirements.txt", "requirements-bot.txt")) {
        $rutaReq = Join-Path $repo $req
        if (Test-Path $rutaReq) {
            Info "  instalando $req"
            & $python -m pip install -q -r $rutaReq 2>&1 | Out-Null
        }
    }
    if (-not (Test-Entorno)) {
        Mal "No se pudieron instalar las dependencias."
        Info "Ejecútalo a mano para ver el error real:"
        Info "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-bot.txt"
        exit 1
    }
}
Bien "Entorno con todas las dependencias."

if (-not (Test-Path $envFile)) {
    Mal "No hay .env. Ejecuta primero .\nodo\instalar.ps1 para configurar el token."
    exit 1
}

$lineas = Get-Content $envFile
$token = (($lineas | Where-Object { $_ -like "TELEGRAM_TOKEN=*" }) -split "=", 2)[1]
if ([string]::IsNullOrWhiteSpace($token)) { Mal "TELEGRAM_TOKEN vacío en .env"; exit 1 }
$token = $token.Trim()

# El token se valida contra Telegram ANTES de arrancar: si está mal, el nodo
# muere igual y el mensaje de Python no lo explica.
Info "Comprobando el token con Telegram..."
try {
    $me = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMe" -TimeoutSec 20
    if (-not $me.ok) { throw "respuesta sin ok" }
    Bien "Token válido: @$($me.result.username)"
    if ($me.result.username -ne "kynicOS_robot") {
        Aviso "Ojo: este token es de @$($me.result.username), no de @kynicOS_robot."
        Aviso "Puede funcionar, pero no es el bot que esperabas."
    }
} catch {
    Mal "El token del .env no es válido para Telegram."
    Info "Suele pasar por pegar el token de otro bot, o uno incompleto."
    Info "Sácalo de @BotFather: /mybots -> tu bot -> API Token."
    Info "Corrígelo con:  notepad .env"
    exit 1
}
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
# Con el nodo haciendo polling, Telegram rechaza una segunda consulta con 409.
# El modelo tarda en cargar, asi que se reintenta hasta 90 s antes de fallar.
$vivo = $false
for ($intento = 1; $intento -le 9; $intento++) {
    try {
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getUpdates?timeout=0&limit=1" -TimeoutSec 15 | Out-Null
        Info "  intento $intento/9: nadie responde todavia..."
    } catch {
        $codigo = $null
        try { $codigo = $_.Exception.Response.StatusCode.value__ } catch { }
        if ($codigo -eq 409) { $vivo = $true; break }
        Info "  intento $intento/9: respuesta inesperada ($codigo)"
    }
    Start-Sleep -Seconds 10
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

Mal "El proceso está vivo, pero Telegram no confirma que escuche."
Info "Esto es lo último que escribió el nodo:"
foreach ($f in @("kynikos.err.log", "kynikos.log")) {
    $ruta = Join-Path $repo $f
    if ((Test-Path $ruta) -and (Get-Item $ruta).Length -gt 0) {
        Write-Host "   --- $f ---" -ForegroundColor DarkGray
        Get-Content $ruta -Tail 15 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
    }
}
Info "Si arriba aparece 401 o Unauthorized, el token del .env no sirve."
Info "Si aparece 409, hay otra ventana con el nodo abierto: ciérrala y repite."
exit 1
