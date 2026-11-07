#Requires -Version 7.0
<#
    Publica el nodo en un solo paso: actualiza el codigo, reinicia, verifica que
    el PID que atiende es el que se lanzo, comprueba la API protegida y abre el
    tunel publico.

    Uso:
        .\nodo\publicar.ps1              actualiza, reinicia, verifica y abre tunel
        .\nodo\publicar.ps1 -SinTunel    lo mismo pero sin abrir el tunel

    Existe porque cada publicacion eran cinco comandos a mano y dos de ellos se
    olvidaban (mirar el PID y comprobar el token).
#>
[CmdletBinding()]
param(
    [switch]$SinTunel,
    [int]$Puerto = 8000
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Paso($t)  { Write-Host ("`n== " + $t) -ForegroundColor Cyan }
function Bien($t)  { Write-Host ("   OK   " + $t) -ForegroundColor Green }
function Mal($t)   { Write-Host ("   ERR  " + $t) -ForegroundColor Red }
function Aviso($t) { Write-Host ("   ...  " + $t) -ForegroundColor Yellow }

$llave = Join-Path $PSScriptRoot "kynikos.ps1"
if (-not (Test-Path $llave)) { Mal "no encuentro nodo\kynikos.ps1"; exit 1 }

# El script del nodo termina con exit; se invoca en un proceso aparte para que no
# cierre este y poder seguir verificando.
$nombreExe = if ($IsWindows) { "pwsh.exe" } else { "pwsh" }
$pwshExe = if ($PSVersionTable.PSEdition -eq "Core") {
    Join-Path $PSHOME $nombreExe
} else { "powershell.exe" }

function Invocar-Nodo {
    param([string[]]$Argumentos)
    # Out-Host manda la salida a la consola sin emitirla por el pipeline: si se
    # dejaba pasar, la funcion devolvia un Object[] con el texto del subproceso
    # mas el codigo, y la comparacion con 0 daba siempre "no arranco".
    & $pwshExe -NoProfile -ExecutionPolicy Bypass -File $llave @Argumentos | Out-Host
    return $LASTEXITCODE
}

# ---------------------------------------------------------------- 1. actualizar
Paso "Actualizar"
try {
    git fetch --quiet origin 2>&1 | Out-Null
    $atras = [int](git rev-list --count HEAD..origin/main)
    $sucio = (git status --porcelain --untracked-files=no)
    if ($sucio) { Aviso "hay cambios locales sin commitear; el avance puede fallar" }
    if ($atras -gt 0) {
        git merge --ff-only origin/main 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Mal "no pude avanzar sin conflicto; revisa: git status"
            exit 1
        }
        Bien ("traidos " + $atras + " commits")
    } else {
        Bien "ya estaba al dia"
    }
} catch {
    Aviso "sin conexion a git; sigo con el codigo local"
}

# ----------------------------------------------------------------- 2. reiniciar
Paso "Reiniciar"
if ((Invocar-Nodo @("reiniciar")) -ne 0) { Mal "el nodo no arranco"; exit 1 }

# ------------------------------------------------------------------ 3. verificar
Paso "Verificar"
if ((Invocar-Nodo @("api")) -ne 0) {
    Mal "la API no respondio; el nodo arranco pero no atiende bien"
    Aviso "mira el diagnostico: escribe /instalar al bot"
    exit 1
}

$estado = & $pwshExe -NoProfile -ExecutionPolicy Bypass -File $llave "estado"
$estado | Out-Host
if ($estado -match "sin KYNIKOS_API_TOKEN") {
    Mal "el nodo no tiene token: no abras el tunel"
    exit 1
}

# --------------------------------------------------------------------- 4. tunel
if ($SinTunel) {
    Aviso "tunel omitido (-SinTunel)"
    Bien "publicacion local lista"
    exit 0
}

Paso "Tunel"
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf) {
    Mal "cloudflared no esta instalado"
    Aviso "instalalo con: winget install --id Cloudflare.cloudflared"
    Aviso "despues cierra esta ventana, abre otra y repite este script"
    exit 1
}

Bien "nodo verificado: abriendo tunel"
Aviso ("URL publica en unos segundos; Ctrl+C para cerrar")
Aviso "expuesto: PWA y /api/health · cerrado con token: /api/status y /api/persona"
& $cf.Source tunnel --url ("http://localhost:" + $Puerto)
