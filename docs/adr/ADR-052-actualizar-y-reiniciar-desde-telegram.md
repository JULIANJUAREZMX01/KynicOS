# ADR-052: Actualizar y reiniciar el nodo desde Telegram

## Contexto
Operar el nodo exigía estar frente a la PC: `/reiniciar` solo confirmaba que el
polling estaba vivo y remitía a la consola. El 6-nov Julián quedó lejos del
equipo con tres commits pendientes de aplicar, imposible de resolver desde el
teléfono. El riesgo real no es la actualización, es quedarse sin nodo y sin
saberlo.

Se descartó matar el updater desde el propio handler: eso cancela la tarea que
atiende el mensaje y el bot queda mudo (pasó el 6-nov).

## Decisión
1. `/actualizar`: `git fetch` + `git merge --ff-only origin/main` y luego lanza
   un proceso **externo** (`kynikos.ps1 reiniciar`) desacoplado, con 5 s de
   espera para que el mensaje de confirmación salga antes de que muera el
   proceso viejo. El proceso externo sobrevive a la muerte del bot.
2. Si el merge no avanza en línea recta (cambios locales o conflicto), **no
   reinicia**: informa el conflicto y deja el nodo como estaba.
3. Aviso de arranque: al levantar el polling, el nodo manda a Julián commit,
   PID y límite de salida. Es la prueba de que volvió. Si el aviso no llega,
   algo falló.
4. `max_tokens_salida` pasa de 768 a 320 en `app/config/schema.py`, y
   `_max_salida()` lo lee de ahí (con `KYNIKOS_MAX_SALIDA` por encima). Así
   `/info`, `/estado` y el límite real dicen el mismo número.

## Consecuencias
- Actualizar ya no exige terminal.
- Un conflicto de git deja el nodo vivo y avisa, en vez de arriesgarlo.
- El aviso de arranque es la única señal de vida tras un reinicio remoto.
- La primera aplicación de este cambio sí necesita consola (el nodo actual no
  conoce `/actualizar`); de ahí en adelante el ciclo se cierra desde Telegram.
