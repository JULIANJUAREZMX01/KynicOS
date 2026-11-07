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

function Probar-Token($token) {
    # Devuelve "ok:<usuario>", "invalido" o "sin_red".
    # Antes, un fallo de red se pintaba igual que un token revocado y el estado
    # decia "sin token valido" con el bot respondiendo en Telegram.
    if ([string]::IsNullOrWhiteSpace($token)) { return "invalido" }
    try {
        $r = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMe" -TimeoutSec 12 -ErrorAction Stop
        if ($r.ok) { return "ok:" + $r.result.username }
        return "invalido"
    } catch {
        $codigo = 0
        try { $codigo = [int]$_.Exception.Response.StatusCode } catch { }
        if ($codigo -eq 401 -or $codigo -eq 404) { return "invalido" }
        return "sin_red"
    }
}

function Test-Token($token) {
    $r = Probar-Token $token
    if ($r -like "ok:*") { return $r.Substring(3) }
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
    $ids = @()

    # 1) cmdlet nativo: no depende del idioma del sistema.
    try {
        foreach ($c in (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction Stop)) {
            $ids += [int]$c.OwningProcess
        }
    } catch { }
    if ($ids.Count -gt 0) { return @($ids | Sort-Object -Unique) }

    # 2) netstat de respaldo. NO se busca 'LISTENING': en Windows en espanol
    #    el estado se llama 'ESCUCHANDO', y el detector devolvia vacio siempre
    #    aunque uvicorn dijera 'Uvicorn running on 0.0.0.0:8000'. Se filtra por
    #    la direccion LOCAL (primer campo) y se toma el PID final de la linea.
    $salida = @()
    try { $salida = netstat -ano 2>$null } catch { return @() }
    $local = "^\s*TCP\s+\S*[:.]$puerto\s"
    $final = "(\d+)\s*$"
    foreach ($linea in $salida) {
        if (($linea -match $local) -and ($linea -match $final)) {
            $ids += [int]$Matches[1]
        }
    }
    return @($ids | Sort-Object -Unique)
}

function Test-PuertoLibre($puerto) {
    return ((Get-ProcesoPuerto $puerto).Count -eq 0)
}

# ------------------------------------------------------------------ pasos
function Paso-Repositorio {
    Paso "Repositorio"
    if (-not (Test-Path (Join-Path $repo ".git"))) { Mal "esta carpeta no es un repositorio git"; exit 1 }

    $ErrorActionPreference = "Continue"
    git fetch -q origin 2>$null | Out-Null
    $ErrorActionPreference = "Stop"

    $local = (git rev-parse HEAD 2>$null)
    $remoto = (git rev-parse "origin/main" 2>$null)
    if (-not $remoto) { Aviso "sin conexion con GitHub; sigo con la version local"; return }
    if ($local -eq $remoto) {
        Bien ("ya en la ultima version (" + $local.Substring(0,7) + ")")
        return
    }

    $hay = (git rev-list --count "HEAD..origin/main" 2>$null)
    $suyos = (git rev-list --count "origin/main..HEAD" 2>$null)
    if ([int]$suyos -gt 0) {
        Aviso ("tienes " + $suyos + " commit(s) locales sin subir; no toco nada")
        Aviso "para actualizar sin perderlos:  git stash && git pull --ff-only && git stash pop"
        return
    }

    Aviso ("hay " + $hay + " commit(s) nuevos; actualizando sin tocar .env ni .venv")
    $marca = Get-Date -Format "yyyyMMdd-HHmm"
    $ErrorActionPreference = "Continue"
    $salida = (git pull --ff-only 2>&1 | Out-String)

    # Un archivo sin versionar con el mismo nombre que uno del commit nuevo
    # bloquea el avance: git no sobrescribe tu copia. Se aparta con otro nombre
    # (no se borra) y se reintenta. Paso el 6-nov con ADR-034.
    if ($salida -match "untracked working tree files would be overwritten") {
        $choques = @()
        $capturar = $false
        foreach ($l in ($salida -split "`r?`n")) {
            $t = $l.Trim()
            if ($t -match "untracked working tree files would be overwritten") { $capturar = $true; continue }
            if ($capturar) {
                if ($t -eq "" -or $t -match "^(Please|Aborting|error:)") { break }
                if (Test-Path (Join-Path $repo $t)) { $choques += $t }
            }
        }
        foreach ($f in $choques) {
            $destino = "$f.local-$marca"
            try {
                Move-Item -LiteralPath (Join-Path $repo $f) -Destination (Join-Path $repo $destino) -Force
                Aviso ("apartado: " + $f + " -> " + $destino)
            } catch { Aviso ("no pude apartar " + $f) }
        }
        if ($choques.Count -gt 0) { $salida = (git pull --ff-only 2>&1 | Out-String) }
    }

    $ErrorActionPreference = "Stop"
    $nuevo = (git rev-parse HEAD 2>$null)
    if ($nuevo -eq $local) {
        Aviso "no se pudo actualizar; sigo con la version local"
        foreach ($l in ($salida -split "`r?`n")) { if ($l.Trim()) { Write-Host ("   " + $l.Trim()) -ForegroundColor DarkGray } }
    }
    else { Bien ("actualizado a " + $nuevo.Substring(0,7)) }
}

function Get-CommitActual {
    $c = (git -C $repo rev-parse --short HEAD 2>$null)
    if ($c) { return $c.Trim() } else { return "" }
}

function Get-CommitCargado {
    # Commit con el que se lanzo el proceso vivo. Si el repo avanzo y el nodo
    # no se reinicio, el bot corre codigo viejo: los comandos nuevos aparecen
    # en el menu de Telegram pero fallan al pulsarlos.
    $f = Join-Path $repo ".kynikos\commit_cargado"
    if (Test-Path $f) { return ((Get-Content $f -Raw) -replace "\s", "") }
    return ""
}

function Test-CodigoDesfasado($procesoId) {
    # Un sello en disco puede quedar viejo o escribirse de mas. La hora de
    # arranque del proceso no miente: si el proceso nacio antes del ultimo
    # commit, esta ejecutando codigo anterior, se ponga lo que se ponga en
    # .kynikos/commit_cargado.
    try {
        $inicio = (Get-Process -Id $procesoId -ErrorAction Stop).StartTime
        $epoch = 0
        try { $epoch = [int](git -C $repo log -1 --format=%ct HEAD 2>$null) } catch { }
        if ($epoch -le 0) { return $false }
        $commit = [DateTimeOffset]::FromUnixTimeSeconds($epoch).LocalDateTime
        return ($inicio -lt $commit)
    } catch { return $false }
}

function Set-CommitCargado($c) {
    if (-not $c) { return }
    New-Item -ItemType Directory -Force -Path (Join-Path $repo ".kynikos") | Out-Null
    $c | Set-Content (Join-Path $repo ".kynikos\commit_cargado")
}

function Get-HuellaDeps {
    # Huella de los requirements: si cambian, se reinstalan encima del entorno
    # existente. Nunca se borra .venv: recrear el entorno en cada arranque es
    # justo lo que rompia la instalacion.
    $texto = ""
    foreach ($r in @("requirements.txt", "requirements-bot.txt")) {
        $ruta = Join-Path $repo $r
        if (Test-Path $ruta) { $texto += (Get-Content $ruta -Raw) }
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($texto)
    return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join "")
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
        Aviso "creando .venv (solo la primera vez)"
        & python -m venv .venv
        if (-not (Test-Path $script:python)) { Mal "no se creo .venv"; exit 1 }
    }

    $sello = Join-Path $repo ".kynikos\deps.sha"
    $huella = Get-HuellaDeps
    $previa = ""
    if (Test-Path $sello) { $previa = ((Get-Content $sello -Raw) -replace "\s", "") }

    if ((Test-Entorno) -and ($previa -eq $huella)) {
        Bien "entorno intacto y dependencias al dia"
        return
    }

    Aviso "instalando dependencias sobre el entorno existente (no se borra nada)"
    & $script:python -m pip install -q --upgrade pip 2>&1 | Out-Null
    foreach ($r in @("requirements.txt", "requirements-bot.txt")) {
        if (Test-Path (Join-Path $repo $r)) { & $script:python -m pip install -q -r (Join-Path $repo $r) 2>&1 | Out-Null }
    }
    if (-not (Test-Entorno)) {
        Mal "faltan dependencias y no se pudieron instalar"
        Aviso "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-bot.txt"
        exit 1
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $sello) | Out-Null
    $huella | Set-Content $sello
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
    Set-CommitCargado (Get-CommitActual)
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

        # El polling activo es la prueba fuerte: Telegram acepta el token y el
        # bot esta recibiendo. El puerto queda como informacion, porque su
        # deteccion depende de herramientas del sistema que pueden fallar o
        # venir traducidas.
        if ($vivo -and $escucha -and -not $error401) { $ok = $true; break }

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
        @{ command = "info";      description = "Ficha tecnica real del nodo" },
        @{ command = "estado";    description = "Salud del nodo: modelo, RAM, polling" },
        @{ command = "modelo";    description = "Modelo activo y contexto" },
        @{ command = "logs";      description = "Ultimas lineas del registro" },
        @{ command = "version";   description = "Version local frente a la publicada" },
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
    # Al iniciar sesion no basta con lanzar el nodo: hay que comprobar version
    # y dependencias. 'inicio' lo hace en segundos y no descarga nada nuevo.
    $shell = (Get-Command powershell).Source
    $guion = Join-Path $PSScriptRoot "kynikos.ps1"
    $accion = New-ScheduledTaskAction -Execute $shell `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$guion`" inicio" `
        -WorkingDirectory $repo
    $disparo = New-ScheduledTaskTrigger -AtLogOn
    $ajustes = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $script:tareaNombre -Action $accion -Trigger $disparo `
        -Settings $ajustes -Description "Nodo primario KYNIKOS" -Force | Out-Null
    Start-ScheduledTask -TaskName $script:tareaNombre

    # 'inicio' hace fetch, comprueba dependencias y arranca: ocho segundos no
    # alcanzan y el resultado es un falso "no arranco". Se espera de verdad.
    $visto = $false
    for ($i = 1; $i -le 24; $i++) {
        Start-Sleep -Seconds 5
        if (Nodo-Vivo) { $visto = $true; break }
        if ($i % 3 -eq 0) { Aviso ("esperando al nodo... " + ($i * 5) + " s") }
    }

    if ($visto) {
        Bien "tarea registrada y nodo vivo al iniciar sesion"
    } else {
        Mal "la tarea se registro pero el nodo no arranco en 120 s"
        $info = Get-ScheduledTaskInfo -TaskName $script:tareaNombre -ErrorAction SilentlyContinue
        if ($info) {
            Aviso ("ultimo resultado de la tarea: " + $info.LastTaskResult + " (0 = sin error)")
            Aviso ("ultima ejecucion: " + $info.LastRunTime)
        }
        $reg = Join-Path $repo "kynikos.err.log"
        if (Test-Path $reg) {
            Aviso "ultimas lineas del registro de errores:"
            Get-Content $reg -Tail 8 -Encoding UTF8 | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
        }
        Aviso "pruebalo a mano:  & '$script:python' cli\kynikos.py run"
        Aviso "y para ver el estado:  .\nodo\kynikos.ps1 estado"
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

    # Verificacion de cada reinicio: actualiza si hay version nueva, revisa
    # dependencias y arranca solo si hace falta. No borra .venv, ni .env, ni
    # el modelo, ni la sesion.
    "inicio" {
        Paso-Repositorio
        $m = "qwen2.5:7b"
        $envActual = Leer-Env
        if ($envActual.ContainsKey("OLLAMA_MODEL") -and $envActual["OLLAMA_MODEL"]) { $m = $envActual["OLLAMA_MODEL"] }
        Paso-Entorno $m
        if (-not (Test-Path $script:python)) { exit 1 }
        if (Nodo-Vivo) { Bien "el nodo ya estaba corriendo; no se duplica" }
        else { Paso-Arrancar }
        if (Paso-Validar) { exit 0 } else { exit 1 }
    }

    "instalar"   { Paso-Requisitos; $m = Paso-Modelo; Paso-Entorno $m }
    "configurar" { Paso-Config "qwen2.5:7b" }
    "arrancar"   { Paso-Arrancar }
    "validar"    { if (Paso-Validar) { exit 0 } else { exit 1 } }
    "detener"    { Paso-Detener }
    "reparar"    {
        Paso "Reparacion"
        if (-not (Test-Entorno)) { Paso-Entorno "qwen2.5:7b" }
        $cargado = Get-CommitCargado
        $actual = Get-CommitActual
        $vivo = Nodo-Vivo
        if ($vivo -and $cargado -and $actual -and ($cargado -ne $actual)) {
            Aviso ("el nodo corre " + $cargado + " y el repositorio esta en " + $actual)
            Aviso "reiniciando para cargar el codigo nuevo"
            Paso-Detener
            Paso-Arrancar
        } elseif ($vivo) {
            Bien ("el nodo ya corre la version " + $actual + "; nada que reparar")
        } else {
            Aviso "el nodo no esta corriendo; arrancando"
            Paso-Arrancar
        }
        if (Paso-Validar) { exit 0 } else { exit 1 }
    }
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
        $p = Nodo-Vivo
        $t = Probar-Token (Leer-Env)["TELEGRAM_TOKEN"]
        if ($t -like "ok:*") { Bien ("token de @" + $t.Substring(3)) }
        elseif ($p) { Bien "token sin verificar ahora, pero el nodo esta polleando: el token sirve" }
        elseif ($t -eq "sin_red") { Aviso "no pude comprobar el token: sin salida a Telegram en este momento" }
        else { Mal "token invalido en .env" }
        if ($p) {
            Bien "corriendo (PID $($p[0].ProcessId))"
            $cargado = Get-CommitCargado
            $actual = Get-CommitActual
            if (Test-CodigoDesfasado $p[0].ProcessId) {
                Aviso ("el proceso arranco antes del ultimo commit (" + $actual + ")")
                Aviso "el bot sigue con codigo viejo; ejecuta: .\nodo\kynikos.ps1 reparar"
            }
        } else { Aviso "detenido" }
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
