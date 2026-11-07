# ADR-058: Comandos del ecosistema, reimplementados a mano

## Contexto
Se intentó aplicar `conectar_ecosystem_py.patch`, descargado de otra app de Base44.
Falló con `patch does not apply` en `app/cloud/telegram_bot.py:69`: el parche
esperaba un contexto que ya no existe porque el archivo cambió con ADR-050
(formato HTML), ADR-052 (`/actualizar`) y ADR-057 (autoconocimiento).

El módulo `app/core/ecosystem.py` ya existía y funcionaba: `estado()`, `buscar()`,
`leer()`, `inventario()`. Lo único que faltaba era conectarlo al bot.

## Decisión
Reimplementar los tres comandos en el archivo actual, conservando la intención del
parche y corrigiendo lo que el parche no cubría:

1. **`/ecosistema`** — inventario de repos en disco. `estado()` ya devuelve HTML de
   Telegram, así que se envía tal cual, con respaldo a texto plano.
2. **`/ecosistema_buscar texto`** — hallazgos escapados con `html.escape`: un `<`
   dentro de un archivo rompía el parseo y el mensaje no llegaba.
3. **`/ecosistema_leer repo ruta`** — contenido dentro de `<pre>` **escapado**; sin
   eso, cualquier archivo con `<` o `&` tumbaba el mensaje.

Los tres se reservan al dueño con `_es_dueno()`, que **falla cerrado**: sin
`TELEGRAM_USER_ID` configurado, nadie pasa. El parche original solo protegía dos de
los tres, dejando `/ecosistema` —que expone rutas locales del disco— abierto a
cualquiera que encontrara el bot.

## Consecuencias
- El bot puede inventariar, buscar y leer en sus repos permitidos, solo para Julián.
- Ningún archivo secreto se lee: `ecosystem.leer()` falla cerrado ante secretos.
- Verificado: 4 repos configurados y `estado()` genera 398 caracteres sin error.
- Lección: un parche de otra instalación es una propuesta, no un hecho. Se lee su
  intención y se aplica sobre el código real.
