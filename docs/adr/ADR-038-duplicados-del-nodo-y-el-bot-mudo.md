# ADR-038 — Duplicados del nodo dejan al bot mudo por ratos

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

Síntoma reportado: "@kynicos no responde".

Diagnóstico en la PC del jefe:

```
Get-Process python | Select Id, StartTime
   Id StartTime
13644 06/11/2026 07:00:46 p. m.
21748 06/11/2026 07:00:46 p. m.
```

Dos procesos del nodo arrancados en el mismo segundo. El registro muestra el
`/start` recibido (`User 8247886073 started KynicOS bot`) y ninguna respuesta
detrás. Ollama está sano y el modelo `qwen2.5:7b` presente.

Telegram admite **una sola instancia por token**. Dos procesos haciendo
`getUpdates` se pisan: uno recibe el mensaje y el otro recibe `409 Conflict`,
así que el bot responde a ratos o no responde. `Paso-Detener` solo mataba el
proceso que tenía el puerto y el que coincidía con la línea de comandos del
detector: un duplicado que perdió la carrera del puerto sobrevivía.

## Decisión

1. `Get-ProcesosNodo` lista **todos** los python que ejecutan este nodo, sin
   depender de quién tenga el puerto.
2. `Paso-Detener` mata todos esos procesos, no solo el visible.
3. Tras matar, verifica que no quede ninguno; si queda, lo dice con los PIDs y
   sugiere ejecutar como administrador en lugar de seguir adelante.
4. `estado` avisa cuando hay más de un proceso: "Telegram solo admite una
   instancia por token; el bot responde a ratos".
5. Regla operativa: antes de diagnosticar el modelo, contar procesos. Un
   duplicado produce los mismos síntomas que un LLM caído.

## Consecuencias

- El caso "no responde" tiene ahora una causa comprobable y un remedio exacto.
- Riesgo asumido: el filtro casa por línea de comandos (`kynikos.py`,
  `app.main`, `cli/kynikos`). Un python ajeno que mencionara esas cadenas en su
  ruta se mataría también; es improbable en esa máquina y el remedio es peor que
  el riesgo.
- El arranque puede tardar unos segundos más: ahora verifica antes de dar por
  bueno el reinicio.
