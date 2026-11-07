# ADR-049 — El agent loop se inyecta, no se importa

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

`/start` ya saludaba bien, pero cualquier mensaje libre respondía:

```
❌ Agent loop no iniciado
```

Mientras el log del arranque decía, en la misma ejecución:

```
✅ ConciergeAgentLoop (KYNIKOS) OK
```

Las dos cosas eran ciertas a la vez porque eran **dos módulos distintos**.

El handler hacía:

```python
from app.main import _agent_loop, _session_manager
```

Pero el proceso arranca con `python -m app.main`, así que ese código se ejecuta
como **`__main__`**. El `from app.main import` no lee la instancia viva: importa
el archivo **otra vez** bajo el nombre `app.main`, creando un módulo nuevo cuyo
`_agent_loop` sigue en `None` porque su lifespan nunca corrió.

El resultado: el loop existía y funcionaba, pero el handler miraba una copia
vacía. El mismo import cruzado estaba en los dos puentes de WhatsApp
(`whatsapp_bridge.py` y `whatsapp_evolution.py`), listos para fallar igual el día
que se activaran.

## Decisión

1. Nuevo `app/core/runtime.py`: registro compartido con `set_runtime`,
   `get_agent_loop`, `get_session_manager` y `clear_runtime`.
2. `app/main.py` llama `set_runtime(_agent_loop, _session_manager)` en el lifespan,
   justo antes de lanzar el bot.
3. `start_telegram_bot` acepta el loop y el session manager como parámetros y los
   guarda; el handler los usa y, si llegan vacíos, cae al registro compartido.
4. Los dos puentes de WhatsApp leen del registro. **Ningún canal importa de
   `app.main`.**

## Consecuencias

- Los mensajes libres de Telegram pasan a procesarse con el loop real.
- El bug estaba latente en WhatsApp y se corrigió antes de encenderlo, no después.
- Verificado: `set_runtime` con dos objetos devuelve esos objetos desde los
  getters, y `clear_runtime` vuelve a `None`. `py_compile` limpio en los cinco
  archivos tocados y `grep` confirma cero `from app.main import` en código.
- Regla derivada, aplicable a todo el repo: **un canal nunca importa el módulo de
  arranque; recibe sus dependencias o las pide al registro.**
