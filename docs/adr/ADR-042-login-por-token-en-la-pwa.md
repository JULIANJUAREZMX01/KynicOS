# ADR-042 — La PWA pide token y lo guarda en el navegador

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

Con el nodo publicado por el túnel, la PWA quedaba visible para cualquiera que
tuviera el enlace. La API ya estaba cerrada (ADR-040 y ADR-041), pero la interfaz
mostraba la consola sin pedir nada y no enviaba credencial alguna, así que
tampoco podía leer el estado del nodo.

Un detalle incómodo: la PWA llamaba a `/api/telegram/salud`, un endpoint del
router de webhook que **no está montado en el nodo local**. Por eso el indicador
de estado decía "inalcanzable" aunque el nodo estuviera perfecto.

## Decisión

1. Nuevo campo de token en la sección **Nodo**, de tipo `password`, que se guarda
   en `localStorage` como `kynikos_token`.
2. Botón **Olvidar token**: lo borra del navegador y vuelve a comprobar.
3. Función `cabeceras()` que añade `X-Kynikos-Token` a toda petición al nodo. El
   token viaja solo al nodo configurado, que es el propio equipo del jefe.
4. El indicador de estado distingue cinco casos, en vez de uno solo:
   sin configurar, inalcanzable, **falta token**, **API cerrada (503)** y activo.
5. La comprobación usa dos rutas: `/api/health` (pública) para saber si el nodo
   vive, y `/api/status` (con token) para leer la persona. Así se separa "no
   llego" de "no tengo permiso", que era el fallo de diagnóstico anterior.
6. Si el chat responde 401, la consola lo dice con la instrucción exacta en vez
   de mostrar un error genérico.

## Consecuencias

- Sintaxis del script validada con `node --check`.
- El token no se escribe en el HTML ni viaja en la URL: va en cabecera y solo si
  el usuario lo guarda.
- Riesgo asumido y explícito: `localStorage` es legible por cualquier script del
  mismo origen. Mitigación razonable aquí porque la PWA se sirve desde el propio
  nodo, sin terceros ni contenido externo. Si algún día se sirve junto a
  contenido de terceros, hay que pasar a cookie `HttpOnly`.
- La PWA sigue siendo una interfaz local: sin token, el nodo no le entrega datos,
  pero el HTML se descarga igual. Ocultar la interfaz requeriría autenticación
  en el servidor, y eso es una decisión aparte.
