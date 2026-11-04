# automatico.ps1 — arranque sin decidir nada.
#
#   .\nodo\automatico.ps1
#
# Hace todo en orden y no pregunta: entorno, dependencias, duplicados, arranque
# y validacion. Si ya esta arriba, no arranca otra instancia.
#
# La validacion NO es por puerto ni por netstat: pregunta a /api/status y exige
# agent_loop=true y telegram_token=true. Un puerto abierto no prueba que el bot
# escuche; un 200 tampoco, porque el endpoint respondia igual con el agente
# caido. Ese fue el falso "FALLO el nodo no esta escuchando" de esta tarde.

[CmdletBinding()]
param(
    [int]$Puerto = 8000,
    [int]$EsperaSegundos = 120
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$py = Join-Path $repo ".venv\Scripts\python.exe"
$url = "http://127.0.0.1:$Puerto/api/status"

function Ok($t)    { Write-Host "   OK    $t" -ForegroundColor Green }
function Malo($t)  { Write-Host "   FALLO $t" -ForegroundColor Red }
function Aviso($t) { Write-Host "   ...   $t" -ForegroundColor DarkGray }

function Leer-Estado {
    try {
        return Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 4
    } catch {
        return $null
    }
}

function Sano($e) {
    if (-not $e) { return $false }
    return ($e.agent_loop -eq $true) -and ($e.telegram_token -eq $true)
}

function Pids-Puerto($p) {
    $ids = @()
    $patron = "[:.]$p\s+\S+\s+LISTENING\s+(\d+)"
    foreach ($linea in (netstat -ano 2>$null)) {
        $m = [regex]::Match($linea, $patron, 'IgnoreCase')
        if ($m.Success) { $ids += [int]$m.Groups[1].Value }
    }
    return @($ids | Sort-Object -Unique)
}

Write-Host ""
Write-Host "== KYNIKOS automatico" -ForegroundColor Yellow

# 1. Ya esta arriba? Entonces no se toca.
$estado = Leer-Estado
if (Sano $estado) {
    $ids = Pids-Puerto $Puerto
    Ok "ya estaba arriba; no se duplica (PID $($ids -join ', '))"
    Write-Host "   pid=$($estado.pid) persona=$($estado.persona) canales=$($estado.channels -join '+')" -ForegroundColor DarkGray
    exit 0
}
if ($estado) {
    Aviso "responde pero incompleto; se reinicia limpio"
}

# 2. Entorno
if (-not (Test-Path $py)) {
    Aviso "creando .venv en la raiz"
    & python -m venv (Join-Path $repo ".venv")
    if (-not (Test-Path $py)) { Malo "no se pudo crear el entorno"; exit 1 }
}
Ok "entorno en la raiz"

& $py -c "import telegram, loguru, httpx" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Aviso "faltan dependencias; instalando (esto tarda)"
    & $py -m pip install -q --upgrade pip 2>&1 | Out-Null
    foreach ($req in @("requirements.txt", "requirements-bot.txt")) {
        $ruta = Join-Path $repo $req
        if (Test-Path $ruta) { & $py -m pip install -q -r $ruta 2>&1 | Out-Null }
    }
    & $py -c "import telegram, loguru, httpx" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { Malo "las dependencias no quedaron; corre instalar"; exit 1 }
}
Ok "telegram, loguru y httpx disponibles"

# 3. Una sola instancia
$ids = Pids-Puerto $Puerto
if ($ids.Count -gt 0) {
    Aviso "deteniendo $($ids.Count) proceso(s) en el puerto $Puerto"
    foreach ($procId in $ids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    for ($i = 0; $i -lt 20; $i++) {
        if ((Pids-Puerto $Puerto).Count -eq 0) { break }
        Start-Sleep -Milliseconds 300
    }
}
if ((Pids-Puerto $Puerto).Count -gt 0) {
    Malo "el puerto $Puerto sigue ocupado por algo que no cede"
    exit 1
}
Ok "puerto $Puerto libre"

# 4. Arranque, con logs separados (el mismo archivo para stdout y stderr revienta)
$dir = Join-Path $repo "logs"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$salida = Join-Path $dir "nodo.out.log"
$errores = Join-Path $dir "nodo.err.log"

$proc = Start-Process -FilePath $py -ArgumentList "cli\kynikos.py", "run" `
    -WorkingDirectory $repo -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $salida -RedirectStandardError $errores
Ok "lanzado con PID $($proc.Id)"

# 5. Verificacion honesta, por HTTP
$limite = (Get-Date).AddSeconds($EsperaSegundos)
$estado = $null
while ((Get-Date) -lt $limite) {
    Start-Sleep -Seconds 3
    if ($proc.HasExited) { break }
    $estado = Leer-Estado
    if (Sano $estado) { break }
}

Write-Host ""
if (Sano $estado) {
    Write-Host "  =================================================" -ForegroundColor Green
    Write-Host "  NODO ARRIBA: agente activo y Telegram conectado" -ForegroundColor Green
    Write-Host "  =================================================" -ForegroundColor Green
    Write-Host "   pid $($estado.pid)  persona $($estado.persona)  canales $($estado.channels -join '+')" -ForegroundColor DarkGray
    Write-Host "   escribe /estado a @kynicOS_robot para cerrar el circulo" -ForegroundColor DarkGray
    exit 0
}

# 6. Fallar diciendo la verdad
if ($proc.HasExited) {
    Malo "el proceso murio al arrancar"
} elseif ($estado) {
    Malo "responde pero no esta completo"
    if ($estado.agent_loop -ne $true)  { Write-Host "   sin agent_loop: el bucle no se construyo" -ForegroundColor DarkGray }
    if ($estado.telegram_token -ne $true) { Write-Host "   sin token: revisa TELEGRAM_TOKEN en .env" -ForegroundColor DarkGray }
} else {
    Malo "no respondio en $EsperaSegundos s"
}
foreach ($f in @($errores, $salida)) {
    if ((Test-Path $f) -and (Get-Item $f).Length -gt 0) {
        Write-Host "   --- $([System.IO.Path]::GetFileName($f)) ---" -ForegroundColor DarkGray
        Get-Content $f -Tail 12 -Encoding UTF8 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
    }
}
exit 1
