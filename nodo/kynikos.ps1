# KYNIKOS - orquestador unico del nodo primario (Windows)
#
# Sustituye a instalar.ps1, configurar.ps1, arrancar-y-validar.ps1,
# arranque-todo-en-uno.ps1, asistente-instalacion.ps1 y registrar-tarea.ps1.
# Esos archivos quedan como alias de este para no romper enlaces ni costumbres.
#
#   .\nodo\kynikos.ps1                 flujo completo (instala, configura, arranca, valida)
#   .\nodo\kynikos.ps1 instalar        solo dependencias, modelo y entorno
#   .\nodo\kynikos.ps1 configurar      solo el .env (pide el token, lo valida)
#   .\nodo\kynikos.ps1 arrancar        lanza el nodo en segundo plano
#   .\nodo\kynikos.ps1 validar         comprueba que Telegram lo escucha
#   .\nodo\kynikos.ps1 estado          resumen: entorno, token, proceso, tarea
#   .\nodo\kynikos.ps1 detener         para el nodo
#   .\nodo\kynikos.ps1 reparar         verifica imports y reinstala lo que falte
#   .\nodo\kynikos.ps1 tarea           arranque automatico al iniciar sesion
#   .\nodo\kynikos.ps1 doctor          diagnostico de la maquina
#   .\nodo\kynikos.ps1 logs            ultimas lineas del nodo
#   .\nodo\kynikos.ps1 comandos        registra el menu de comandos en Telegram
#
# Todo es idempotente: si algo ya esta, no se repite.

param(
    [Parameter(Position = 0)]
    [ValidateSet("auto", "instalar", "configurar", "arrancar", "validar",
                 "estado", "detener", "reparar", "tarea", "doctor", "logs", "comandos", "centro")]
    [string]$Accion = "auto",

    [string]$Modelo = "",
    [switch]$SinTarea
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$script:python = Join-Path $repo ".venv\Scripts\python.exe"
$script:envFile = Join-Path $repo ".env"
$script:tareaNombre = "KYNIKOS nodo"
$script:puerto = if ($env:KYNIKOS_PORT) { [int]$env:KYNIKOS_PORT } else { 8000 }

function Paso($t)  { Write-Host ""; Write-Host "== $t" -ForegroundColor Yellow }
function Bien($t)  { Write-Host "   OK   $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "   $t" -ForegroundColor Cyan }
function Mal($t)   { Write-Host "   FALLO $t" -ForegroundColor Red }

function Actualizar-Ruta {
    $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$m;$u"
    $ollamaDir = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
    if ((Test-Path $ollamaDir) -and ($env:Path -notlike "*$ollamaDir*")) { $env:Path += ";$ollamaDir" }
}

function Leer-Env {
    if (-not (Test-Path $script:envFile)) { return @{} }
    $h = @{}
    foreach ($l in Get-Content $script:envFile) {
        if ($l -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { $h[$Matches[1]] = $Matches[2].Trim() }
    }
    return $h
}

function Invoke-Telegram($token, $metodo) {
    try {
        return Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/$metodo" -TimeoutSec 20
    } catch {
        $codigo = $null
        try { $codigo = $_.Exception.Response.StatusCode.value__ } catch { }
        return [pscustomobject]@{ ok = $false; codigo = $codigo }
    }
}

function Test-Token($token) {
    if ([string]::IsNullOrWhiteSpace($token)) { return $null }
    $r = Invoke-Telegram $token "getMe"
    if ($r.ok) { return $r.result.username }
    return $null
}

function Test-Entorno {
    if (-not (Test-Path $script:python)) { return $false }
    & $script:python -c "import telegram, loguru, httpx" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Nodo-Vivo {
    # Por linea de comandos...
    $p = $null
    try {
        $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
             Where-Object { $_.CommandLine -like "*kynikos.py*run*" -or $_.CommandLine -like "*app.main*" }
    } catch { $p = $null }   # CIM no disponible: se resuelve por puerto mas abajo
    if ($p) { return $p }
    # ...y por puerto: una instancia lanzada por la tarea programada puede tener
    # otra linea de comandos y seguir ocupando el 8000. Eso fue lo que tumbo el
    # arranque con [Errno 10048].
    foreach ($pid in (Get-ProcesoPuerto $script:puerto)) {
        $q = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($q) { return @([pscustomobject]@{ ProcessId = $pid; Name = $q.ProcessName }) }
    }
    return $null
}

function Get-ProcesoPuerto($puerto) {
    # netstat en vez de Get-NetTCPConnection: si el modulo NetTCPIP falla o no
    # esta, el cmdlet devuelve vacio EN SILENCIO y el nodo parece caido aunque
    # uvicorn diga 'Uvicorn running on http://0.0.0.0:8000'. Ese falso negativo
    # dejo a Julian con 'FALLO el nodo no esta escuchando' seis veces seguidas.
    $ids = @()
    $patron = "[:.]$puerto\s+\S+\s+LISTENING\s+(\d+)"
    $salida = @()
    try { $salida = netstat -ano 2>$null } catch { return @() }
    foreach ($linea in $salida) {
        $m = [regex]::Match($linea, $patron, 'IgnoreCase')
        if ($m.Success) { $ids += [int]$m.Groups[1].Value }
    }
    return @($ids | Sort-Object -Unique)
}

function Test-PuertoLibre($puerto) {
    return ((Get-ProcesoPuerto $puerto).Count -eq 0)
}

# ------------------------------------------------------------------ pasos
function Paso-Repositorio {
    Paso "Repositorio"
    if (Test-Path (Join-Path $repo ".git")) {
        $antes = git rev-parse HEAD 2>$null
        git pull -q --ff-only 2>$null | Out-Null
        $despues = git rev-parse HEAD 2>$null
        if ($antes -eq $despues) { Bien "ya estaba al dia" } else { Bien "actualizado a $($despues.Substring(0,7))" }
    } else {
        Mal "esta carpeta no es un repositorio git"
        exit 1
    }
}

function Paso-Requisitos {
    Paso "Requisitos"
    $paquetes = [ordered]@{ git = "Git.Git"; python = "Python.Python.3.12"; ollama = "Ollama.Ollama" }
    $faltan = @($paquetes.Keys | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })
    if ($faltan.Count -eq 0) { Bien "git, python y ollama disponibles"; return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Mal ("faltan " + ($faltan -join ", ") + " y no hay winget")
        Aviso "instalalos desde git-scm.com, python.org y ollama.com"
        exit 1
    }
    foreach ($n in $faltan) {
        Aviso "instalando $n ..."
        & winget install --id $paquetes[$n] -e --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    }
    Actualizar-Ruta
    $siguen = @($paquetes.Keys | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })
    if ($siguen.Count -gt 0) {
        Mal ("instalados pero esta ventana aun no los ve: " + ($siguen -join ", "))
        Aviso "cierra y abre PowerShell, luego repite el mismo comando"
        exit 1
    }
    Bien "git, python y ollama disponibles"
}

function Paso-Modelo {
    Paso "Modelo local"
    $m = if ($Modelo) { $Modelo } else { if ($env:KYNIKOS_MODELO) { $env:KYNIKOS_MODELO } else { "qwen2.5:7b" } }
    $tiene = (& ollama list 2>$null) -match [regex]::Escape($m.Split(":")[0])
    if ($tiene) { Bien "$m ya esta descargado"; return $m }
    Aviso "descargando $m (una sola vez, ~4.7 GB)"
    & ollama pull $m
    if ($LASTEXITCODE -ne 0) { Mal "no se pudo descargar $m"; exit 1 }
    Bien "$m listo"
    return $m
}

function Paso-Entorno($m) {
    Paso "Entorno de Python"
    if (-not (Test-Path $script:python)) {
        Aviso "creando .venv"
        & python -m venv .venv
        if (-not (Test-Path $script:python)) { Mal "no se creo .venv"; exit 1 }
    }
    if (-not (Test-Entorno)) {
        Aviso "instalando dependencias (tarda un poco)"
        & $script:python -m pip install -q --upgrade pip 2>&1 | Out-Null
        foreach ($r in @("requirements.txt", "requirements-bot.txt")) {
            if (Test-Path (Join-Path $repo $r)) { & $script:python -m pip install -q -r $r 2>&1 | Out-Null }
        }
        if (-not (Test-Entorno)) {
            Mal "faltan dependencias y no se pudieron instalar"
            Aviso "prueba a mano para ver el error:"
            Aviso "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-bot.txt"
            exit 1
        }
    }
    Bien "entorno con telegram, loguru y httpx"
}

function Paso-Config($m) {
    Paso "Configuracion"
    $h = Leer-Env
    $usuario = ""
    if ($h.ContainsKey("TELEGRAM_TOKEN")) { $usuario = Test-Token $h["TELEGRAM_TOKEN"] }

    if ($usuario) {
        Bien "token valido de @$usuario"
        if (-not $h.ContainsKey("KYNIKOS_PALABRA_1") -or [string]::IsNullOrWhiteSpace($h["KYNIKOS_PALABRA_1"])) {
            Aviso "falta KYNIKOS_PALABRA_1; el nodo pedira la palabra en cada arranque"
        }
        if (-not $h.ContainsKey("OLLAMA_MODEL")) { Aviso "OLLAMA_MODEL no definido; se usara $m" }
        $env:TELEGRAM_TOKEN = $h["TELEGRAM_TOKEN"]
        return
    }

    Aviso "no hay token valido en .env"
    $seguro = Read-Host "Pega el token de @kynicOS_robot (no se vera)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    $token = $token.Trim()

    $quien = Test-Token $token
    if (-not $quien) {
        Mal "ese token no es valido. Sacalo de @BotFather: /mybots -> API Token"
        exit 1
    }
    Bien "token valido de @$quien"

    if ([string]::IsNullOrWhiteSpace($h["KYNIKOS_PALABRA_1"])) {
        $palabra = Read-Host "Palabra del primer paso (KYNIKOS_PALABRA_1)"
        if ([string]::IsNullOrWhiteSpace($palabra)) { $palabra = "KYNICOS" }
    } else { $palabra = $h["KYNIKOS_PALABRA_1"] }

    if (Test-Path $script:envFile) { Copy-Item $script:envFile "$($script:envFile).anterior" -Force }

    $lineas = @(
        "TELEGRAM_TOKEN=$token",
        "TELEGRAM_USER_ID=8247886073",
        "PERSONA=kynikos",
        "KYNIKOS_PALABRA_1=$palabra",
        "KYNIKOS_ESTADO_DIR=.kynikos",
        "OLLAMA_URL=http://127.0.0.1:11434",
        "OLLAMA_MODEL=$m",
        "OLLAMA_NUM_CTX=4096",
        "MAX_TOKENS_SALIDA=768",
        "TIMEOUT_LLM=300",
        "LOG_LEVEL=INFO"
    )
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($script:envFile, $lineas, $utf8)
    $env:TELEGRAM_TOKEN = $token
    Bien ".env escrito (sin BOM) y respaldo en .env.anterior"
}

function Paso-Detener {
    $ids = @()
    $p = Nodo-Vivo
    if ($p) { $ids += $p.ProcessId }
    $ids += Get-ProcesoPuerto $script:puerto
    $ids = @($ids | Where-Object { $_ } | Select-Object -Unique)

    if ($ids.Count -eq 0) { return }

    foreach ($id in $ids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    # Esperar a que el socket quede libre: Windows tarda en soltarlo.
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        if (Test-PuertoLibre $script:puerto) { break }
    }
    if (Test-PuertoLibre $script:puerto) { Bien "nodo anterior detenido; puerto $script:puerto libre" }
    else {
        Mal "el puerto $script:puerto sigue ocupado por el PID $((Get-ProcesoPuerto $script:puerto) -join ', ')"
        Aviso "abre una consola como administrador y ejecuta:"
        Aviso "  Stop-Process -Id $((Get-ProcesoPuerto $script:puerto) -join ',') -Force"
        exit 1
    }
}

function Paso-Arrancar {
    Paso "Arranque"
    $p = Nodo-Vivo
    if ($p -and -not (Test-PuertoLibre $script:puerto)) {
        Bien "ya estaba corriendo en el puerto $script:puerto (PID $($p[0].ProcessId)); no se duplica"
        return
    }
    if (-not (Test-PuertoLibre $script:puerto)) {
        Mal "el puerto $script:puerto esta ocupado por otro programa, no por el nodo"
        Aviso "mata ese proceso o arranca con otro puerto:  `$env:KYNIKOS_PORT=8010"
        exit 1
    }

    if (Get-ScheduledTask -TaskName $script:tareaNombre -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $script:tareaNombre -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }

    $log = Join-Path $repo "kynikos.log"
    $err = Join-Path $repo "kynikos.err.log"
    $proc = Start-Process -FilePath $script:python -ArgumentList "cli\kynikos.py", "run" `
        -WorkingDirectory $repo -RedirectStandardOutput $log -RedirectStandardError $err `
        -WindowStyle Hidden -PassThru
    Aviso "lanzado con PID $($proc.Id); el modelo tarda en cargar"
    Start-Sleep -Seconds 10

    if ($proc.HasExited) {
        Mal "murio al arrancar; esto dijo:"
        foreach ($f in @($err, $log)) {
            if ((Test-Path $f) -and (Get-Item $f).Length -gt 0) {
                Get-Content $f -Tail 15 -Encoding UTF8 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
            }
        }
        exit 1
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $repo ".kynikos") | Out-Null
    $proc.Id | Set-Content (Join-Path $repo ".kynikos\nodo.pid")
    Bien "proceso vivo (PID $($proc.Id))"
}

function Paso-Validar {
    Paso "Validacion"

    # NO se usa getUpdates para validar. Dos motivos:
    #  1) consume los mensajes del propio bot: cada consulta puede robarlos.
    #  2) mientras el bot procesa un mensaje no esta en long-poll, asi que la
    #     consulta devuelve 200 y parece que nadie escucha. Ese falso negativo
    #     ya nos paso con el bot respondiendo "hi" en el log.
    # Se comprueba lo que de verdad importa: proceso vivo, puerto escuchando y
    # la linea de polling en el log, sin errores de autenticacion.
    $log = Join-Path $repo "kynikos.log"
    $ok = $false
    $motivo = ""

    for ($i = 1; $i -le 6; $i++) {
        $vivo = Nodo-Vivo
        $puerto = -not (Test-PuertoLibre $script:puerto)
        $texto = ""
        if (Test-Path $log) { $texto = (Get-Content $log -Tail 200 -Encoding UTF8) -join "`n" }
        $escucha = $texto -match "polling started"
        $error401 = $texto -match "Unauthorized|401"
        $error409 = $texto -match "Conflict|409"

        if ($vivo -and $puerto -and $escucha -and -not $error401) { $ok = $true; break }

        if ($error401) { $motivo = "el token del .env es rechazado (401)"; break }
        if ($error409) { $motivo = "hay otra instancia haciendo polling (409)"; break }
        Aviso "intento $i/6: levantando (puerto:$puerto polling:$escucha)"
        Start-Sleep -Seconds 5
    }

    if ($ok) {
        Write-Host ""
        Write-Host "  ===============================================" -ForegroundColor Green
        Bien "VALIDADO: el nodo esta escuchando a Telegram"
        Write-Host "  ===============================================" -ForegroundColor Green
        Aviso "prueba final: escribe /estado a @kynicOS_robot"
        Aviso "actividad en vivo:  .\nodo\kynikos.ps1 logs"
        return $true
    }

    Mal "el nodo no esta escuchando"
    if ($motivo) { Aviso "causa probable: $motivo" }
    $ruta = Join-Path $repo "kynikos.err.log"
    if ((Test-Path $ruta) -and (Get-Item $ruta).Length -gt 0) {
        Write-Host "   --- kynikos.err.log ---" -ForegroundColor DarkGray
        Get-Content $ruta -Tail 15 -Encoding UTF8 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
    }
    return $false
}

function Paso-Comandos {
    Paso "Menu de comandos en Telegram"
    $token = (Leer-Env)["TELEGRAM_TOKEN"]
    if ([string]::IsNullOrWhiteSpace($token)) { Mal "no hay token en .env; ejecuta: kynikos.ps1 configurar"; return }

    $quien = Test-Token $token
    if (-not $quien) { Mal "el token del .env no es valido"; return }

    $comandos = @(
        @{ command = "start";     description = "Saludo y estado de KynicOS" },
        @{ command = "estado";    description = "Salud del nodo: modelo, RAM, polling" },
        @{ command = "modelo";    description = "Modelo activo y contexto" },
        @{ command = "logs";      description = "Ultimas lineas del registro" },
        @{ command = "id";        description = "Tu ID de Telegram" },
        @{ command = "reiniciar"; description = "Reinicia el bot" },
        @{ command = "ayuda";     description = "Lista de comandos" }
    )

    $cuerpo = @{ commands = $comandos } | ConvertTo-Json -Depth 4 -Compress
    try {
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/setMyCommands" -Method Post `
            -ContentType "application/json" -Body $cuerpo -TimeoutSec 20 | Out-Null
        Bien "menu de $($comandos.Count) comandos registrado en @$quien"
    } catch {
        Mal "Telegram rechazo el menu: $($_.Exception.Message)"
        return
    }

    $corto = "Perro guardian tecnico. Nodo propio con modelo local: sin techo de tokens."
    $largo = "KYNIKOS, nodo primario de Julian Juarez. Seguridad, infraestructura y automatizacion.`nCorre en hardware propio con modelo local: sin techo de tokens ni coste por consulta.`n`nComandos: /estado /modelo /logs /id /reiniciar /ayuda"

    foreach ($par in @(@{ m = "setMyShortDescription"; k = "short_description"; v = $corto },
                       @{ m = "setMyDescription";      k = "description";       v = $largo })) {
        $b = @{ $($par.k) = $par.v } | ConvertTo-Json -Compress
        try {
            Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/$($par.m)" -Method Post `
                -ContentType "application/json" -Body $b -TimeoutSec 20 | Out-Null
        } catch { Aviso "no se pudo actualizar $($par.m)" }
    }

    $ver = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMyCommands" -TimeoutSec 20
    if ($ver.ok) {
        foreach ($c in $ver.result) { Write-Host ("   /" + $c.command.PadRight(10) + $c.description) -ForegroundColor DarkGray }
    }
    Aviso "revisa el menu en la barra de Telegram junto al campo de texto"
}


function Paso-Tarea {
    Paso "Arranque automatico"
    if (-not (Test-Path $script:python)) { Mal "el nodo no esta instalado"; return }
    $accion = New-ScheduledTaskAction -Execute $script:python -Argument "cli\kynikos.py run" -WorkingDirectory $repo
    $disparo = New-ScheduledTaskTrigger -AtLogOn
    $ajustes = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $script:tareaNombre -Action $accion -Trigger $disparo `
        -Settings $ajustes -Description "Nodo primario KYNIKOS" -Force | Out-Null
    Start-ScheduledTask -TaskName $script:tareaNombre
    Start-Sleep -Seconds 8
    if (Nodo-Vivo) { Bien "tarea registrada y nodo vivo al iniciar sesion" }
    else {
        Mal "la tarea se registro pero el nodo no arranco"
        Aviso "pruebalo a mano:  & '$script:python' cli\kynikos.py run"
    }
}

# ------------------------------------------------------------------ acciones
switch ($Accion) {

    "doctor" {
        Paso "Diagnostico de la maquina"
        $os = Get-CimInstance Win32_OperatingSystem
        $cs = Get-CimInstance Win32_ComputerSystem
        $ram = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
        Aviso "equipo:  $($cs.Name) - $($os.Caption)"
        Aviso "RAM:     $ram GB"
        $disco = Get-PSDrive C -ErrorAction SilentlyContinue
        if ($disco) { Aviso ("disco:   {0} GB libres de {1} GB" -f [math]::Round($disco.Free/1GB,1), [math]::Round(($disco.Free+$disco.Used)/1GB,1)) }
        foreach ($p in @("git","python","ollama")) {
            $c = Get-Command $p -ErrorAction SilentlyContinue
            if ($c) { Aviso ("{0,-7} {1}" -f $p, $c.Source) } else { Mal "$p no instalado" }
        }
        if ($ram -lt 8)      { Aviso "con menos de 8 GB usa qwen2.5:3b" }
        elseif ($ram -lt 14) { Aviso "con $ram GB usa qwen2.5:7b" }
        else                 { Aviso "con $ram GB puedes probar qwen2.5:14b, aunque 7b va mas rapido" }
        if (Test-Entorno) { Bien "entorno de Python completo" } else { Aviso "entorno incompleto: .\nodo\kynikos.ps1 reparar" }
        $u = Test-Token (Leer-Env)["TELEGRAM_TOKEN"]
        if ($u) { Bien "token valido de @$u" } else { Aviso "sin token valido en .env" }
        if (Nodo-Vivo) { Bien "nodo corriendo" } else { Aviso "nodo detenido" }
    }

    "instalar"   { Paso-Requisitos; $m = Paso-Modelo; Paso-Entorno $m }
    "configurar" { Paso-Config "qwen2.5:7b" }
    "arrancar"   { Paso-Arrancar }
    "validar"    { if (Paso-Validar) { exit 0 } else { exit 1 } }
    "detener"    { Paso-Detener }
    "reparar"    { Paso; if (Test-Entorno) { Bien "nada que reparar" } else { Paso-Entorno "qwen2.5:7b" } }
    "tarea"      { Paso-Tarea }
    "comandos"   { Paso-Comandos }
    "centro" {
        $py = Join-Path $repo ".venv\Scripts\python.exe"
        if (-not (Test-Path $py)) { Mal "falta el entorno; corre primero: .\nodo\kynikos.ps1 instalar"; exit 1 }
        & $py (Join-Path $repo "nodo\centro.py")
        exit $LASTEXITCODE
    }
    "logs" {
        foreach ($f in @("kynikos.log","kynikos.err.log")) {
            $ruta = Join-Path $repo $f
            if ((Test-Path $ruta) -and (Get-Item $ruta).Length -gt 0) {
                Write-Host "   --- $f ---" -ForegroundColor DarkGray
                Get-Content $ruta -Tail 25 -Encoding UTF8 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
            }
        }
    }
    "estado" {
        Paso "Estado del nodo"
        if (Test-Entorno) { Bien "entorno completo" } else { Aviso "entorno incompleto" }
        $u = Test-Token (Leer-Env)["TELEGRAM_TOKEN"]
        if ($u) { Bien "token de @$u" } else { Mal "sin token valido" }
        $p = Nodo-Vivo
        if ($p) { Bien "corriendo (PID $($p[0].ProcessId))" } else { Aviso "detenido" }
        $t = Get-ScheduledTask -TaskName $script:tareaNombre -ErrorAction SilentlyContinue
        if ($t) { Bien "tarea de arranque registrada" } else { Aviso "sin tarea de arranque" }
    }
    default {
        Paso "KYNIKOS - flujo completo"
        Paso-Repositorio
        Paso-Requisitos
        $m = Paso-Modelo
        Paso-Entorno $m
        Paso-Config $m
        Paso-Detener
        Paso-Arrancar
        $ok = Paso-Validar
        # La persistencia se decide por el proceso vivo, no por la validacion:
        # un falso negativo no debe dejar la maquina sin arranque automatico.
        if (-not $SinTarea -and (Nodo-Vivo)) { Paso-Tarea }
        if (-not $ok) { exit 1 }
    }
}
