# ADR-057: Autoconocimiento veraz y detección HVAC sin duplicados

## Contexto
Cuatro fallos detectados el 7-nov mientras Julián probaba el bot en Telegram.

**1. El bot negaba sus propias capacidades.** Al preguntarle en qué se diferencia de
otros bots de Telegram respondió que *no tiene acceso al disco*, que *no puede
ejecutar comandos* y que *no tiene interfaces gráficas*. Las tres cosas son falsas:
corre en la PC del jefe, lee logs y memoria, ejecuta git y `kynikos.ps1`, y sirve el
centro de mando en el puerto 8000. Un asistente que se subestima así es inútil para
diagnóstico.

**2. `/info` mentía en dos campos.** Anunciaba `salida 768` cuando el límite efectivo
era 320, y listaba 2 skills cuando hay 6. Los valores estaban escritos a mano.

**3. El .env heredado mantenía 768.** Cambiar el default en el código no basta si la
instalación ya tiene el valor viejo escrito; el aviso de arranque del nodo
(`Salida max: 768 tokens`) fue justo lo que lo delató.

**4. La detección de HVAC fallaba de dos maneras.** Existía `gotea_agua` desde antes y
se añadió un `fuga_agua` duplicado sin revisar el archivo completo. Además `ac` se
comparaba como subcadena: `"hace ruido"` contiene `h-a-c-e` y disparaba un falso
positivo, mientras `"no enfría nada"` no se detectaba porque el huésped no nombra el
equipo.

## Decisión
- `bloque_sistema()` declara el acceso real y **prohíbe** afirmar lo contrario, con los
  límites verdaderos (sin GPU, no navega sola, un solo autorizado).
- `datos()` lee las skills del disco y normaliza 768 → 320, así `/info` no puede mentir.
- `Settings` normaliza `max_tokens_salida = 768` → 320 con `field_validator`; cualquier
  otro valor se respeta.
- HVAC: se elimina el `fuga_agua` duplicado y se reutiliza `gotea_agua`. La detección
  usa `\b(ac|a/c|hvac)\b` y una lista de síntomas que el huésped dice sin nombrar el
  equipo (`enfría`, `calor`, `templado`, `gotea`, `fuga`).

## Consecuencias
- Verificado: `no enfría nada` → `no_enfria`; `hace ruido` → None; `el aire hace ruido`
  → `ruido_raro`; `gotea agua el minisplit` → `gotea_agua`; `toalla extra` → None.
- `/info` reporta 6 skills y salida 320.
- 49 pruebas siguen verdes.
- Regla: al extender una base de conocimiento, leer el archivo completo antes de añadir
  una entrada; el duplicado silencioso es peor que el hueco.
