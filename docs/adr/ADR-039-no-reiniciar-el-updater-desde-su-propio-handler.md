# ADR-039 — No reiniciar el updater desde su propio handler

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

El comando `/reiniciar` del bot ejecutaba, dentro del propio handler:

```python
await update.message.reply_text("Reiniciando el bot...")
await stop_telegram_bot()      # detiene el updater
await asyncio.sleep(2)
await start_telegram_bot()     # nunca se ejecutaba
```

`stop_telegram_bot()` detiene el updater, y detener el updater **cancela la tarea
que está ejecutando ese mismo handler**. Las líneas siguientes nunca corren.

Resultado observado el 6-nov-2026: el bot respondió "Reiniciando el bot..." y
después quedó mudo. Ni `/estado` respondía. Solo se recuperó al reiniciar el
proceso desde la PC.

## Decisión

1. `/reiniciar` **no toca el updater**. Si el polling está vivo, lo confirma y
   explica por qué no lo reinicia.
2. Si el polling está caído, lo levanta: ahí no hay updater que cancelar, así que
   es seguro.
3. El reinicio real se hace desde la PC con `.\nodo\kynikos.ps1 reiniciar`, que
   ya demuestra el cambio de PID.
4. El mensaje del comando incluye el comando exacto, para que el jefe no dependa
   de recordarlo.

## Consecuencias

- El comando deja de ser una trampa: no puede dejar al bot sin polling.
- Se pierde la capacidad de "limpiar sesión" desde Telegram. Si algún día hace
  falta, se implementa con un task independiente creado con `asyncio.create_task`
  que sobreviva al handler, no deteniendo el updater en línea.
- Regla general: nunca detener el updater dentro de un handler suyo. Un bot que
  se apaga a sí mismo no puede volver a encenderse.
