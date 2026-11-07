# ADR-044 — El nodo local monta el canal web

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

La PWA mostraba `(sin respuesta)` a cada mensaje aunque el indicador dijera
"nodo: kynikos" en verde. El diagnóstico era simple y ya estaba detectado: la
PWA llama a `POST /api/chat`, pero ese router **solo se montaba en `api/index.py`**
(el despliegue serverless), nunca en `app/main.py`, que es el que corre en la PC.

Resultado: 404 → `d.respuesta` indefinido → `(sin respuesta)`. El nodo estaba
sano y el mensaje no llegaba a ninguna parte.

## Decisión

Montar el router de `app/channels/web_chat` en `app/main.py`, junto al de
WhatsApp y el dashboard, con el mismo patrón tolerante: si el import falla, el
nodo sigue arrancando y lo registra en el log.

El router ya venía protegido por `requiere_token_web` (ADR-042), así que al
montarlo hereda la exigencia de token.

## Consecuencias

- Verificado: `POST /api/chat` sin token → **401**; con token → **200** con
  respuesta del handler (en el sandbox sin Ollama devuelve el error del
  proveedor, que es el comportamiento correcto).
- La PWA ya puede conversar con el nodo local, que era el propósito original de
  la consola.
- El error del proveedor se devuelve con código 200 y campo `error`; la PWA lo
  muestra tal cual. Se deja así a propósito: si un día hay varios proveedores,
  un fallo parcial no debe romper la respuesta.
