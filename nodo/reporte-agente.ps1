<#
.SYNOPSIS
  Reporta el estado del nodo KynicOS al agente y deja constancia local.
.DESCRIPTION
  Revisa repositorio, puerto, endpoint /api/status, variables de entorno (solo
  nombres) y pruebas. Envia un reporte corto al agente por su API. Si no hay
  llave de API, guarda el reporte en nodo\logs y no falla.
.EXAMPLE
  .\nodo\reporte-agente.ps1 -SelfTest
.EXAMPLE
  .\nodo\reporte-agente.ps1 -RunTests
.EXAMPLE
  .\nodo\reporte-agente.ps1 -Watch -IntervalMinutes 360
#>
[CmdletBinding()]
param(
  [string]$RepoPath = (Get-Location).Path,
  [int]$Port = 8000,
  [string]$AgentBaseUrl = 'https://app.base44.com/api/agents/69cfdbf8f38ae270ee9fcf0d',
  [string]$ApiKey = $env:BASE44_AGENT_API_KEY,
  [string]$ConversationId = $env:BASE44_AGENT_CONVERSATION,
  [string]$TaskName = 'KYNIKOS nodo',
  [switch]$SelfTest,
  [switch]$RunTests,
  [switch]$NoSend,
  [switch]$Watch,
  [int]$IntervalMinutes = 360
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
$logDir = Join-Path $RepoPath 'nodo\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Paso($m) { Write-Host "  $m" }

function Get-Repo {
  $out = [ordered]@{ branch = 'n/d'; commit = 'n/d'; dirty = $false; ok = $false }
  if (Test-Path (Join-Path $RepoPath '.git')) {
    $b = & git -C $RepoPath rev-parse --abbrev-ref HEAD 2>$null
    $c = & git -C $RepoPath rev-parse --short HEAD 2>$null
    $d = & git -C $RepoPath status --porcelain 2>$null
    if ($b) { $out.branch = "$b".Trim() }
    if ($c) { $out.commit = "$c".Trim() }
    $out.dirty = [bool]$d
    $out.ok = $true
  }
  [pscustomobject]$out
}

function Test-Puerto([int]$p) {
  $cliente = New-Object Net.Sockets.TcpClient
  try {
    $conexion = $cliente.BeginConnect('127.0.0.1', $p, $null, $null)
    if ($conexion.AsyncWaitHandle.WaitOne(1200)) { $cliente.EndConnect($conexion); $cliente.Close(); return $true }
    return $false
  } catch {
    return $false
  } finally {
    if ($cliente) { $cliente.Dispose() }
  }
}

function Get-ApiEstado([int]$p) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$p/api/status" -TimeoutSec 6
    return $r.Content
  } catch {
    return $null
  }
}

function Get-Variables {
  $ejemplo = Join-Path $RepoPath '.env.example'
  $real = Join-Path $RepoPath '.env'
  $faltan = @(); $total = 0
  if (Test-Path $ejemplo) {
    $esperadas = @()
    Get-Content $ejemplo | ForEach-Object {
      if ($_ -match '^([A-Z0-9_]+)=') { $esperadas += $Matches[1] }
    }
    $total = $esperadas.Count
    if (Test-Path $real) {
      $puestas = @()
      Get-Content $real | ForEach-Object {
        if ($_ -match '^([A-Z0-9_]+)=(.+)$') { if ($Matches[2].Trim().Length -gt 0) { $puestas += $Matches[1] } }
      }
      foreach ($v in $esperadas) { if ($puestas -notcontains $v) { $faltan += $v } }
    } else {
      $faltan = $esperadas
    }
  }
  [pscustomobject]@{ total = $total; faltan = $faltan; hay_env = (Test-Path $real) }
}

function Get-Tarea {
  try {
    $r = & schtasks /query /tn $TaskName /fo LIST 2>$null
    if ($LASTEXITCODE -eq 0) { return 'registrada' } else { return 'no registrada' }
  } catch { return 'n/d' }
}

function Get-Pruebas {
  if (-not $RunTests) { return 'omitidas' }
  Push-Location $RepoPath
  try {
    $py = Join-Path $RepoPath '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { $py = 'python' }
    $salida = & $py -m pytest -q 2>&1 | Select-Object -Last 5
    $texto = ($salida -join ' ').Trim()
    if ($texto -match '(\d+) (failed|error)') { return "fallan: $texto" }
    if ($texto -match 'passed') { return "ok: $texto" }
    return "sin resumen: $texto"
  } catch {
    return 'no se pudo correr pytest'
  } finally {
    Pop-Location
  }
}

function Get-Nodo {
  # Un PID o un estado "Ready" no prueban nada. Lo que prueba que el nodo
  # atiende es el conflicto 409 de Telegram: solo ocurre si alguien mas esta
  # consumiendo getUpdates, es decir, si el nodo esta escuchando de verdad.
  $proc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
          Where-Object { $_.CommandLine -like '*kynikos.py*run*' }
  $pidNodo = ($proc | Select-Object -First 1).ProcessId
  $telegram = $false
  $detalle = 'sin token en .env'
  $envFile = Join-Path $RepoPath '.env'
  if (Test-Path $envFile) {
    $linea = Get-Content $envFile | Where-Object { $_ -like 'TELEGRAM_TOKEN=*' } | Select-Object -First 1
    if ($linea) {
      $tok = ($linea -split '=', 2)[1].Trim()
      if ($tok.Length -gt 10) {
        try {
          Invoke-RestMethod -Uri "https://api.telegram.org/bot$tok/getUpdates?timeout=0&limit=1" -TimeoutSec 15 | Out-Null
          $detalle = 'nadie escucha (sin conflicto)'
        } catch {
          $codigo = $null
          try { $codigo = $_.Exception.Response.StatusCode.value__ } catch { }
          if ($codigo -eq 409) { $telegram = $true; $detalle = 'escuchando (409)' }
          else { $detalle = "error de red o token: $codigo" }
        }
      }
    }
  }
  [pscustomobject]@{ vivo = [bool]$proc; pid = $pidNodo; telegram = $telegram; detalle = $detalle }
}

function Get-Nodo {
  # Un PID o un estado "Ready" no prueban nada. Lo que prueba que el nodo
  # atiende es el conflicto 409 de Telegram: solo ocurre si alguien mas esta
  # consumiendo getUpdates, es decir, si el nodo esta escuchando de verdad.
  $proc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
          Where-Object { $_.CommandLine -like '*kynikos.py*run*' }
  $pidNodo = ($proc | Select-Object -First 1).ProcessId
  $telegram = $false
  $detalle = 'sin token en .env'
  $envFile = Join-Path $RepoPath '.env'
  if (Test-Path $envFile) {
    $linea = Get-Content $envFile | Where-Object { $_ -like 'TELEGRAM_TOKEN=*' } | Select-Object -First 1
    if ($linea) {
      $tok = ($linea -split '=', 2)[1].Trim()
      if ($tok.Length -gt 10) {
        try {
          Invoke-RestMethod -Uri "https://api.telegram.org/bot$tok/getUpdates?timeout=0&limit=1" -TimeoutSec 15 | Out-Null
          $detalle = 'nadie escucha (sin conflicto)'
        } catch {
          $codigo = $null
          try { $codigo = $_.Exception.Response.StatusCode.value__ } catch { }
          if ($codigo -eq 409) { $telegram = $true; $detalle = 'escuchando (409)' }
          else { $detalle = "error de red o token: $codigo" }
        }
      }
    }
  }
  [pscustomobject]@{ vivo = [bool]$proc; pid = $pidNodo; telegram = $telegram; detalle = $detalle }
}

function Send-AlAgente([string]$texto, [string]$rutaLog) {
  $registro = [ordered]@{
    fecha = $stamp
    enviado = $false
    motivo = ''
    status = $null
    conversacion = $ConversationId
    reporte = $texto
  }
  if ($NoSend) { $registro.motivo = 'NoSend activo' }
  elseif (-not $ApiKey) { $registro.motivo = 'falta BASE44_AGENT_API_KEY' }
  else {
    $headers = @{ api_key = $ApiKey }
    if (-not $ConversationId) {
      try {
        $convs = Invoke-RestMethod -Uri "$AgentBaseUrl/conversations" -Headers $headers -Method Get -TimeoutSec 25
        if ($convs -is [array] -and $convs.Count -gt 0) { $ConversationId = $convs[0].id }
        elseif ($convs.conversations -and $convs.conversations.Count -gt 0) { $ConversationId = $convs.conversations[0].id }
        elseif ($convs.id) { $ConversationId = $convs.id }
      } catch {
        $registro.motivo = "no se pudo listar conversaciones: $($_.Exception.Message)"
      }
    }
    $uri = if ($ConversationId) { "$AgentBaseUrl/conversations/$ConversationId/messages" } else { "$AgentBaseUrl/messages" }
    $cuerpo = @{ role = 'user'; content = $texto } | ConvertTo-Json -Depth 4
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers $headers -Method Post -Body $cuerpo -ContentType 'application/json' -TimeoutSec 90
      $registro.enviado = $true
      $registro.status = $resp.StatusCode
      $registro.conversacion = $ConversationId
    } catch {
      $registro.motivo = "$($_.Exception.Message)"
    }
  }
  ($registro | ConvertTo-Json -Depth 4) | Set-Content -Path $rutaLog -Encoding UTF8
  [pscustomobject]$registro
}

function Invoke-Reporte {
  Write-Host ''
  Write-Host "KynicOS - reporte al agente ($stamp)"
  $repo = Get-Repo
  Write-Paso "repo: $($repo.branch) @ $($repo.commit) $(if($repo.dirty){'(con cambios sin commit)'}else{'(limpio)'})"

  $puerto = Test-Puerto $Port
  Write-Paso "puerto ${Port}: $(if($puerto){'escuchando'}else{'cerrado'})"

  $api = if ($puerto) { Get-ApiEstado $Port } else { $null }
  Write-Paso "api/status: $(if($api){'responde'}else{'sin respuesta'})"

  $vars = Get-Variables
  Write-Paso "variables: $($vars.total - $vars.faltan.Count)/$($vars.total) con valor; faltan: $(if($vars.faltan.Count){$vars.faltan -join ', '}else{'ninguna'})"

  $nodo = Get-Nodo
  Write-Paso "nodo: $(if($nodo.vivo){"proceso vivo (PID $($nodo.pid))"}else{'proceso ausente'})"
  Write-Paso "telegram: $($nodo.detalle)"

  $nodo = Get-Nodo
  Write-Paso "nodo: $(if($nodo.vivo){"proceso vivo (PID $($nodo.pid))"}else{'proceso ausente'})"
  Write-Paso "telegram: $($nodo.detalle)"

  $tarea = Get-Tarea
  Write-Paso "tarea programada '$TaskName': $tarea"

  $pruebas = Get-Pruebas
  Write-Paso "pruebas: $pruebas"

  $partes = @()
  $partes += "REPORTE KYNICOS $stamp"
  $partes += "repo $($repo.branch)@$($repo.commit)$(if($repo.dirty){' +cambios'})"
  $partes += "puerto $Port $(if($puerto){'activo'}else{'caido'})"
  $partes += "api $(if($api){'ok'}else{'sin respuesta'})"
  $partes += "vars $($vars.total - $vars.faltan.Count)/$($vars.total)"
  if ($vars.faltan.Count) { $partes += "faltan $($vars.faltan -join ',')" }
  $partes += "nodo $(if($nodo.vivo){'vivo'}else{'ausente'})"
  $partes += "telegram $(if($nodo.telegram){'escuchando'}else{'mudo'})"
  $partes += "nodo $(if($nodo.vivo){'vivo'}else{'ausente'})"
  $partes += "telegram $(if($nodo.telegram){'escuchando'}else{'mudo'})"
  $partes += "tarea $tarea"
  $partes += "pruebas $pruebas"
  $texto = $partes -join ' | '

  $rutaLog = Join-Path $logDir ("reporte-" + (Get-Date -Format 'yyyyMMdd-HHmm') + '.json')
  $res = Send-AlAgente $texto $rutaLog

  if ($res.enviado) { Write-Paso "enviado al agente (HTTP $($res.status))" }
  else { Write-Paso "no enviado: $($res.motivo). Guardado en $rutaLog" }
  if ($SelfTest -and $res.reporte) { Write-Host ''; Write-Host 'Texto enviado:'; Write-Host $res.reporte }
  Write-Host ''
}

if ($Watch) {
  Write-Host "Modo continuo: cada $IntervalMinutes minutos. Ctrl+C para salir."
  while ($true) {
    Invoke-Reporte
    Start-Sleep -Seconds ($IntervalMinutes * 60)
  }
} else {
  Invoke-Reporte
}
