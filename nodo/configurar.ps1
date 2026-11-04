# CONFIGURAR — escribe el .env del nodo y valida el token
#
# Existe para que no haya que pegar lineas sueltas en PowerShell, que es lo
# que estaba rompiendo la configuracion. Pide el token una vez, lo comprueba
# contra Telegram y escribe el archivo completo.

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $raiz ".env"

Write-Host ""
Write-Host "== KYNIKOS · configurar el nodo" -ForegroundColor Yellow
Write-Host ""

$seguro = Read-Host "Pega el token de @kynicOS_robot (no se verá en pantalla)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
$token = $token.Trim()

if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "   No escribiste nada. Nada que hacer." -ForegroundColor Red
    exit 1
}

Write-Host "   Comprobando con Telegram..." -ForegroundColor Cyan
try {
    $me = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getMe" -TimeoutSec 20
} catch {
    Write-Host "   Ese token no es válido. Sácalo de @BotFather: /mybots -> API Token" -ForegroundColor Red
    exit 1
}
Write-Host "   Válido: @$($me.result.username)" -ForegroundColor Green

if ($me.result.username -ne "kynicOS_robot") {
    Write-Host "   Ojo: es @$($me.result.username), no @kynicOS_robot." -ForegroundColor Yellow
    $sigo = Read-Host "   ¿Continuar de todas formas? (s/n)"
    if ($sigo -ne "s") { exit 1 }
}

if (Test-Path $envFile) {
    $respaldo = "$envFile.anterior"
    Copy-Item $envFile $respaldo -Force
    Write-Host "   El anterior quedó guardado como .env.anterior" -ForegroundColor DarkGray
}

$lineas = @(
    "TELEGRAM_TOKEN=$token",
    "TELEGRAM_USER_ID=8247886073",
    "PERSONA=kynikos",
    "KYNIKOS_PALABRA_1=KYNICOS",
    "KYNIKOS_ESTADO_DIR=.kynikos",
    "OLLAMA_URL=http://127.0.0.1:11434",
    "OLLAMA_MODEL=qwen2.5:7b",
    "OLLAMA_NUM_CTX=4096",
    "MAX_TOKENS_SALIDA=768",
    "TIMEOUT_LLM=300",
    "LOG_LEVEL=INFO"
)

# Sin BOM: un .env con BOM rompe la primera clave al leerlo.
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($envFile, $lineas, $utf8)

Write-Host ""
Write-Host "   .env escrito en $envFile" -ForegroundColor Green
Write-Host "   Token, tu ID, palabra del primer paso y modelo: todo puesto." -ForegroundColor Green
Write-Host ""
Write-Host "   Siguiente paso: doble clic en nodo\ARRANCAR.cmd" -ForegroundColor Yellow
Write-Host ""
