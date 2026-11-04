<#
.SYNOPSIS
  Asistente de instalacion y monitoreo del nodo KynicOS. Reporta al agente y recibe su guia.
.DESCRIPTION
  Diagnostica el nodo (repo, puerto, /api/status, variables del .env, tarea programada y pruebas),
  arma una linea de estado y la envia al agente por su API. La respuesta del agente se imprime
  en la consola y, si no hay conexion, el reporte queda en nodo\logs\reporte-<fecha>.log.
.PARAMETER Fase
  Reporta una fase puntual: preflight, deps, env, telegram, service, validate, tests, done.
.PARAMETER Detalle
  Texto libre que se manda junto con la fase (un error, un mensaje de Telegram, lo que sea).
.PARAMETER Watch
  Repite el reporte cada IntervalMinutes minutos. Pensado para dejarlo corriendo.
.EXAMPLE
  .\asistente-instalacion.ps1 -SelfTest
.EXAMPLE
  .\asistente-instalacion.ps1 -Fase telegram -Detalle "getMe devuelve 401 Unauthorized"
.EXAMPLE
  .\asistente-instalacion.ps1 -Watch -IntervalMinutes 30
#>
[CmdletBinding()]
param(
  [string]$RepoPath = (Get-Location).Path,
  [int]$Port = 8000,
  [string]$AgentBaseUrl = "https://app.base44.com/api/agents/69d1042a619569bfe891119e",
  [string]$ApiKey = $env:BASE44_AGENT_API_KEY,
  [string]$ConversationId = $env:BASE44_AGENT_CONVERSATION,
  [string]$Fase = "",
  [string]$Detalle = "",
  [switch]$SelfTest,
  [switch]$RunTests,
  [switch]$Watch,
  [int]$IntervalMinutes = 30
)

$ErrorActionPreference = 'Continue'
$logDir = Join-Path $RepoPath 'nodo\logs'
$runId = (Get-Date -Format 'yyyyMMdd-HHmm')

function Write-Local {
  param([string]$Texto)
  try {
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Add-Content -Path (Join-Path $logDir ("reporte-{0}.log" -f (Get-Date -Format 'yyyy-MM-dd'))) -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Texto)
  } catch { }
}

function Get-RepoInfo {
  $out = @{ branch = 'sin-repo'; commit = 'sin-git' }
  if (Test-Path (Join-Path $RepoPath '.git')) {
    $b = & git -C $RepoPath rev-parse --abbrev-ref HEAD 2>$null
    $c = & git -C $RepoPath rev-parse --short HEAD 2>$null
    if ($b) { $out.branch = $b.Trim() }
    if ($c) { $out.commit = $c.Trim() }
  }
  return $out
}

function Test-Puerto {
  param([int]$p)
  try {
    $cliente = New-Object Net.Sockets.TcpClient
    $ok = $cliente.ConnectAsync('127.0.0.1', $p).Wait(1500)
    $cliente.Close()
    return $ok
  } catch { return $false }
}

function Get-ApiCodigo {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/api/status" -f $Port) -TimeoutSec 5
    return [int]$r.StatusCode
  } catch { return 0 }
}

function Get-Faltantes {
  param([string]$dir)
  $ejemplo = Join-Path $dir '.env.example'
  $real = Join-Path $dir '.env'
  if (-not (Test-Path $ejemplo)) { return @('sin .env.example') }
  if (-not (Test-Path $real)) { return @('.env ausente: copia .env.example') }

  $claves = @()
  Get-Content $ejemplo | ForEach-Object {
    if ($_ -match '^\s*([A-Z0-9_]+)\s*=') { $claves += $matches[1] }
  }
  $puestas = @{}
  Get-Content $real | ForEach-Object {
    if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.+)$' -and $matches[2].Trim() -ne '') { $puestas[$matches[1]] = $true }
  }
  $faltan = @()
  foreach ($k in $claves) { if (-not $puestas.ContainsKey($k)) { $faltan += $k } }
  return $faltan
}

function Get-TareaRegistrada {
  try {
    $r = & schtasks /query /tn 'KynicOS' 2>$null
    if ($LASTEXITCODE -eq 0) { return $true } else { return $false }
  } catch { return $false }
}

function Send-AlAgente {
  param([string]$Texto)

  if (-not $ApiKey) {
    Write-Host "  [sin llave] guardo el reporte en $logDir" -ForegroundColor Yellow
    Write-Local $Texto
    return
  }

  $headers = @{ 'api_key' = $ApiKey; 'Content-Type' = 'application/json' }

  if (-not $ConversationId) {
    try {
      $resp = Invoke-RestMethod -Uri ("{0}/conversations" -f $AgentBaseUrl) -Headers $headers -Method Get -TimeoutSec 20
      if ($resp -is [array] -and $resp.Count -gt 0) { $script:ConversationId = $resp[0].id }
      elseif ($resp.conversations -and $resp.conversations.Count -gt 0) { $script:ConversationId = $resp.conversations[0].id }
      elseif ($resp.id) { $script:ConversationId = $resp.id }
    } catch {
      Write-Host "  no pude listar conversaciones: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }

  $uri = if ($script:ConversationId) { "{0}/conversations/{1}/messages" -f $AgentBaseUrl, $script:ConversationId } else { "{0}/messages" -f $AgentBaseUrl }
  $body = @{ role = 'user'; content = $Texto } | ConvertTo-Json -Depth 4

  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers $headers -Method Post -Body $body -TimeoutSec 90
    Write-Host ""
    Write-Host "  respuesta del agente ($($r.StatusCode)):" -ForegroundColor Green
    try {
      $j = $r.Content | ConvertFrom-Json
      $txt = $j.content
      if (-not $txt) { $txt = $j.message }
      if (-not $txt) { $txt = $r.Content }
      Write-Host ("  " + $txt)
    } catch { Write-Host ("  " + $r.Content) }
    Write-Local ("ENVIADO {0} -> {1}" -f $uri, $Texto)
  } catch {
    Write-Host "  fallo el envio: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Local ("PENDIENTE ENVIO: {0}" -f $Texto)
  }
}

function Invoke-Reporte {
  $repo = Get-RepoInfo
  $puerto = if (Test-Puerto $Port) { 'escuchando' } else { 'cerrado' }
  $api = Get-ApiCodigo
  $faltan = @(Get-Faltantes $RepoPath)
  $tarea = if (Get-TareaRegistrada) { 'registrada' } else { 'no registrada' }
  $pruebas = 'no ejecutadas'

  if ($RunTests) {
    $venv = Join-Path $RepoPath '.venv\Scripts\python.exe'
    $py = if (Test-Path $venv) { $venv } else { 'python' }
    try {
      $salida = & $py -m pytest -q 2>&1 | Select-Object -Last 3
      $pruebas = ($salida -join ' ').Trim()
      if ($pruebas.Length -gt 90) { $pruebas = $pruebas.Substring(0, 90) }
    } catch { $pruebas = 'pytest no disponible' }
  }

  $faseTxt = if ($Fase) { $Fase } else { 'diagnostico' }
  $detTxt = if ($Detalle) { $Detalle } else { '' }
  $faltanTxt = if ($faltan.Count -eq 0) { 'ninguna' } else { ($faltan -join ',') }

  $linea = "REPORTE KYNICOS run=$runId fase=$faseTxt | repo=$($repo.branch)@$($repo.commit) | puerto=$puerto | api=$api | tarea=$tarea | faltan=$faltanTxt | pruebas=$pruebas"
  if ($detTxt) { $linea = $linea + " | detalle=$detTxt" }

  Write-Host ""
  Write-Host "  $linea" -ForegroundColor Cyan
  Send-AlAgente $linea
  Write-Local $linea
}

if ($SelfTest) {
  Write-Host "Probando conexion con el agente..." -ForegroundColor Cyan
  if (-not $ApiKey) { Write-Host "  falta BASE44_AGENT_API_KEY. Generala en el panel Developer / API Docs del agente." -ForegroundColor Yellow; exit 2 }
  Send-AlAgente "SELFTEST run=$runId desde $env:COMPUTERNAME. Responde con una linea si me escuchas."
  exit 0
}

if ($Watch) {
  Write-Host "Monitoreo continuo cada $IntervalMinutes minutos. Ctrl+C para salir." -ForegroundColor Cyan
  while ($true) {
    Invoke-Reporte
    Start-Sleep -Seconds ($IntervalMinutes * 60)
  }
}

Invoke-Reporte
