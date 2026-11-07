# ADR-035 — Detección de intención por palabra completa y enlaces vivos

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

El bot @kynicOS_robot recibió un saludo y contestó como concierge de transporte
público, con un enlace a `querutamellevacancun.onrender.com`, servicio suspendido
por facturación desde abril y que devuelve HTTP 503 desde entonces.

La detección de consultas de transporte usaba `kw in mensaje`. Eso hizo que:

| Mensaje del usuario | Se detectaba como | Motivo |
|---|---|---|
| "busco un hotel" | transporte | el `bus` de *busco* |
| "buscar trabajo" | transporte | el `bus` de *buscar* |
| "quiero ir a dormir" | transporte | la expresión `ir a` |

Además, el bucle evaluaba `ctx.messages[-1]` sin comprobar el rol: si el último
elemento era una respuesta previa del propio bot hablando de rutas, la skill se
realimentaba sola.

## Decisión

1. La detección usa expresión regular con límites de palabra, no coincidencia de
   subcadenas. Los acentos se respetan en los límites.
2. Se eliminan los disparadores genéricos que en español producen falsos
   positivos: `bus`, `ir a`, `llegar a`.
3. El bucle evalúa solo el mensaje más reciente con rol `user`, nunca la última
   respuesta del asistente.
4. Toda URL de la app de rutas apunta a `mueve-cancun-sigma.vercel.app`, el
   entorno vivo (HTTP 200). Render queda fuera hasta que se resuelva la
   suspensión por facturación.

## Consecuencias

- El bot deja de contestar con rutas a quien saluda o busca otra cosa.
- Los enlaces que se envían a un huésped responden.
- Se verificaron once casos, incluidos los tres falsos positivos originales,
  con cero fallos. La suite sigue en 40 verdes.
- Riesgo asumido: la lista de palabras es finita; una consulta de transporte
  formulada con términos ausentes irá al LLM general, que es el comportamiento
  aceptable por defecto.
