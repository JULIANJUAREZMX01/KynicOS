# Registra el nodo para que arranque solo al iniciar sesion.
# Uso:  .\nodo\registrar-tarea.ps1
# Falla fuerte si el nodo todavia no esta instalado, en vez de crear una tarea vacia.

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo ".venv\Scripts\python.exe"
$envFile = Join-Path $repo ".env"

if (-not (Test-Path $python)) {
    Write-Host "NO SE REGISTRO NADA: no existe $python" -ForegroundColor Red
    Write-Host "El nodo aun no esta instalado. Ejecuta primero:  .\nodo\instalar.ps1" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $envFile)) {
    Write-Host "NO SE REGISTRO NADA: falta el archivo .env" -ForegroundColor Red
    Write-Host "Ejecuta primero:  .\nodo\instalar.ps1" -ForegroundColor Yellow
    exit 1
}

$accion  = New-ScheduledTaskAction -Execute $python -Argument "cli\kynikos.py run" -WorkingDirectory $repo
$disparo = New-ScheduledTaskTrigger -AtLogOn
$ajustes = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "KYNIKOS nodo" -Action $accion -Trigger $disparo -Settings $ajustes -Description "Nodo primario KYNIKOS" -Force | Out-Null
Start-ScheduledTask -TaskName "KYNIKOS nodo"

# Comprobacion real: esperar y confirmar que el proceso sigue vivo, no solo "Ready"
Start-Sleep -Seconds 8
$info = Get-ScheduledTaskInfo -TaskName "KYNIKOS nodo"
$vivo = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*kynikos.py*run*" }

if ($vivo) {
    Write-Host "OK: el nodo esta corriendo (PID $($vivo[0].ProcessId))." -ForegroundColor Green
    Write-Host "Escribe /estado a @kynicOS_robot para confirmarlo." -ForegroundColor Green
} else {
    Write-Host "LA TAREA SE REGISTRO PERO EL NODO NO ESTA VIVO." -ForegroundColor Red
    Write-Host "Ultimo resultado de Windows: $($info.LastTaskResult)" -ForegroundColor Yellow
    Write-Host "Ejecutalo a mano para ver el error real:" -ForegroundColor Yellow
    Write-Host "  & `'$python`' cli\kynikos.py run"
    exit 1
}
