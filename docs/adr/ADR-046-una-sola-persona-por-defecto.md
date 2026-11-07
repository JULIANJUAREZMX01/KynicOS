# ADR-046 — Una sola persona por defecto en todo el nodo

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

En producción salían dos identidades a la vez: `/info`, `/version`, `/estado` y
los logs decían **KYNIKOS**, pero `/start` saludaba como **Leo**, el concierge de
lujo de hotel.

La causa no era la persona, era el **respaldo**:

| Sitio | Cómo leía la persona | Respaldo |
|---|---|---|
| `/api/status`, `/api/persona`, agente | `os.getenv("PERSONA", Settings().persona)` | `Settings.persona` = `"kynicos"` |
| `telegram_bot.start` | `os.getenv("PERSONA", "leo")` | literal `"leo"` |

Con un `.env` **sin** `PERSONA`, cada uno caía en un valor distinto. La variable
faltaba en el archivo real aunque `.env.example` sí la traía (`PERSONA=leo`), lo
que además explica por qué el ejemplo apuntaba al hotel.

## Decisión

1. `/start` lee la persona exactamente igual que el resto:
   `get_persona(os.getenv("PERSONA", Settings().persona))`.
2. El respaldo del `except` pasa a ser el saludo de KYNIKOS, no uno genérico.
3. Regla: **ningún módulo inventa su propio valor por defecto** para una variable
   que ya tiene dueño en `Settings`.

## Consecuencias

- Verificado en los logs del nodo real: `ConciergeAgentLoop — Persona: KYNIKOS`
  y `KYNICOS OS ACTIVO — Persona: KYNIKOS`. El núcleo nunca estuvo mal.
- `/start` pasa a responder "🛡️ KYNIKOS en línea. ¿Qué atacamos hoy, jefe?".
- Queda pendiente cosmético: el log dice `ConciergeAgentLoop` (y emoji de hotel)
  aunque la persona sea KYNIKOS. Se conserva porque el módulo se sigue llamando
  así y renombrarlo toca imports; no afecta comportamiento.
