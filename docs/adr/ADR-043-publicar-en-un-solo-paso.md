# ADR-043 — Publicar el nodo en un solo comando

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

Publicar el nodo eran cinco comandos a mano: `git fetch`, `git merge`,
`reiniciar`, `api` y el túnel. En la práctica se olvidaban dos de los importantes:
comprobar que el PID que atiende es el que se lanzó, y comprobar que el token
existe antes de exponer el nodo.

El jefe pidió que el agente lo hiciera todo. No es posible: el agente ejecuta
PowerShell 7.4.6 en un contenedor **Debian Linux**, sin acceso a su PC Windows.
La alternativa útil no es pedirle más pasos, sino reducir la publicación a uno.

## Decisión

Nuevo `nodo/publicar.ps1` con cuatro fases y parada en seco en cada fallo:

1. **Actualizar** — `fetch` + `merge --ff-only`; si hay divergencia, para.
2. **Reiniciar** — delega en `kynikos.ps1 reiniciar` en un proceso aparte (el
   script del nodo termina con `exit` y cerraría este).
3. **Verificar** — invoca `api` y `estado`; si la API falla o falta el token,
   **no abre el túnel**.
4. **Túnel** — solo con lo anterior en verde.

`-SinTunel` para publicar sin exponer.

## Consecuencias

- Verificado con un repositorio y un nodo simulados, en tres casos:
  al día (sale 0), un commit pendiente en origin (actualiza y sale 0) y nodo que
  no arranca (sale 1 sin abrir el túnel).
- **Fallo encontrado durante la prueba y corregido:** la función `Invocar-Nodo`
  emitía la salida del subproceso por el pipeline, así que devolvía un `Object[]`
  con el texto y el código. La comparación `-ne 0` daba siempre verdadero y el
  script habría dicho "el nodo no arrancó" con el nodo perfecto. Se corrigió con
  `| Out-Host`, que muestra sin emitir.
- Segundo fallo corregido: `git status --porcelain` contaba archivos no rastreados
  como cambios pendientes. Ahora usa `--untracked-files=no`.
- Límite asumido y explícito: el agente no puede ejecutar nada en el host del
  jefe. Este script es la forma de que su intervención sea un solo comando.
