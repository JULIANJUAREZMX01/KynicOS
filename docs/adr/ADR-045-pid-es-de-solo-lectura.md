# ADR-045 — El nodo no puede usar `$PID` como variable

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

`nodo/kynikos.ps1 reiniciar` dejó de funcionar de golpe con un error que no
parecía del proyecto:

```
kynikos.ps1: No se puede sobrescribir la variable PID porque es de solo lectura o constante.
```

La causa: `$PID` es una **variable automática de PowerShell** que contiene el
identificador del proceso actual, y es constante. El script la reutilizaba como
variable de iteración dentro de `Nodo-Vivo`:

```powershell
foreach ($pid in (Get-ProcesoPuerto $script:puerto)) { ... }
```

PowerShell aborta al intentar asignarla. El fallo era intermitente porque solo se
ejecuta cuando la detección por CIM no encuentra el proceso y hay que resolverlo
por puerto: justo el caso de una instancia lanzada por la tarea programada.

Segundo hallazgo en la misma traza:

```
FALLO el puerto 8000 sigue ocupado por el PID 0
  Stop-Process -Id 0 -Force
```

`OwningProcess = 0` significa "el sistema no identifica el dueño", no un proceso.
El script lo trataba como PID real y proponía matarlo. `Stop-Process -Id 0` no
libera nada y confunde.

## Decisión

1. La variable de iteración pasa a llamarse `$procId`. Regla: nunca se usan
   `$PID`, `$HOME`, `$HOST`, `$PSHOME` ni `$LASTEXITCODE` como variables propias.
2. `Get-ProcesoPuerto` descarta los ceros antes de devolver.
3. Si el puerto está ocupado y no hay PID visible, el mensaje **no** propone
   matar nada: pide `Get-NetTCPConnection -LocalPort 8000 -State Listen` para
   ver el dueño, y sugiere reiniciar el equipo si no aparece.

## Consecuencias

- Verificado en PowerShell 7.4.6 real, no por inspección: el patrón viejo
  reproduce exactamente el error del jefe; el nuevo itera sin tocarlo y `$PID`
  queda intacto (devolvió 15761 en la prueba).
- Filtro del cero verificado: de `@(0, 4242)` devuelve `4242`.
- Es el tercer bug de esta serie que solo aparece al ejecutar, no al leer: los
  otros dos fueron el retorno contaminado de `publicar.ps1` y el `404` del chat.
