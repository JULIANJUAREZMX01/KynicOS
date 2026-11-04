# ADR-030 — Verificación por API, no por puerto

- **Estado:** aceptado
- **Fecha:** 3 de noviembre de 2026
- **Sustituye en la práctica:** el chequeo de puerto de ADR-025 (verificación de doble paso) para el nodo primario
- **Relacionado:** ADR-021 (nodo primario), ADR-027 (orquestador único)

## Contexto

El nodo local estaba levantado y atendiendo Telegram, y el validador decía lo contrario. Seis intentos consecutivos de `arrancar-y-validar.ps1` terminaron en `FALLO el nodo no esta escuchando`, mientras `kynikos.err.log` mostraba `Uvicorn running on http://0.0.0.0:8000` y el polling respondía.

Dos causas, ambas de instrumentación y no del nodo:

1. `Get-NetTCPConnection` devuelve vacío **en silencio** cuando el módulo NetTCPIP no está disponible o falla. El validador interpretó "no lo veo" como "no está".
2. `/api/status` devolvía `"status": "ok"` escrito a mano en el código. El endpoint respondía 200 con el agente caído y sin token de Telegram, así que un 200 tampoco probaba nada.

Resultado: dos señales, una que mentía por defecto y otra que mentía por diseño.

## Decisión

1. La salud del nodo se mide en `GET /api/status`, exigiendo `agent_loop = true` **y** `telegram_token = true`.
2. El endpoint calcula su propio estado: `ok` solo si ambas condiciones se cumplen; en cualquier otro caso `degradado`, exponiendo `pid`, `agent_loop` y `telegram_token`.
3. El puerto se usa únicamente para detectar y liberar duplicados. Nunca como prueba de salud.
4. Los lanzadores escriben stdout y stderr en archivos distintos. `Start-Process` rechaza ambas redirecciones al mismo archivo, y con `-NoNewWindow` además no es válido.
5. Ningún lanzador usa `--reload` en el nodo: duplica el proceso, deja dos PIDs en el puerto y compite por el long-poll de Telegram.

## Consecuencias

**Positivas.** El falso negativo desaparece. Un nodo sin token deja de reportarse sano. Los logs separados permiten distinguir un fallo de arranque de un fallo de aplicación.

**Negativas.** `/api/status` es ahora más estricto que antes: instalaciones sin `TELEGRAM_TOKEN` reportan `degradado` aunque el resto funcione. Es intencional, porque el nodo existe para atender ese canal.

**Riesgo residual.** Si el proceso vive pero el long-poll de Telegram murió, `agent_loop` sigue en `true`. La comprobación que lo detecta es `/estado` dos veces con un minuto de diferencia: mismo PID y el contador de minutos subiendo.

## Alternativas descartadas

- **`Get-CimInstance Win32_Process` para leer líneas de comando.** Sirve para identificar duplicados, no para probar salud: el proceso puede existir y estar atascado.
- **`getUpdates` como termómetro.** Puede devolver 200 en el hueco entre long-polls y además roba mensajes pendientes del bot.
- **Dejar `status` fijo en `ok`.** Es lo que provocó este ADR.
