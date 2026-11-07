# ADR-048 — Manifest y service worker en la raíz, y espera real al soltar el puerto

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

Dos síntomas distintos del mismo tipo: cosas que "casi" funcionan.

**1. Tres 404 en el centro de mando.** Al abrir `http://localhost:8000` el log
mostraba:

```
GET /pkg/wasm_busqueda.js       404
GET /manifest.webmanifest       404
GET /sw.js                      404
```

`web/manifest.webmanifest` y `web/sw.js` **existían**, pero solo estaban
montados bajo `/static`. El navegador los pide en la raíz, y un service worker
solo controla el ámbito **desde el que se sirve**: bajo `/static` no cubriría la
página. Sin `sw.js` no hay modo offline.

El tercero es distinto: `wasm-busqueda/` solo tiene `Cargo.toml`, `README.md` y
`src/`. Nunca se compiló con wasm-pack, así que `pkg/wasm_busqueda.js` no existe
en ninguna parte. El frontend ya lo maneja: cae a "respaldo JS" con búsqueda
simple.

**2. Reinicio que falla una vez y funciona a la segunda.** Con el mensaje nuevo
del PID 0, el jefe vio "el puerto 8000 esta ocupado pero no puedo ver que proceso
lo tiene", y el comando siguiente arrancó sin tocar nada. La espera era de 10s y
uvicorn tiene proceso hijo: no alcanzaba.

## Decisión

1. Rutas explícitas `GET /manifest.webmanifest` y `GET /sw.js` con `FileResponse`
   desde `web/`, con el tipo MIME correcto y `Cache-Control: no-cache` para el
   service worker (si se cachea, las actualizaciones no llegan nunca).
2. La espera al soltar el puerto sube a 20s. A mitad de camino, si el dueño es
   visible, se cierra solo: es el nodo anterior, no un proceso ajeno.
3. El WASM **no** se compila aquí. Requiere Rust y wasm-pack en la PC, y el
   respaldo JS mantiene la búsqueda usable. Queda como pendiente explícito.

## Consecuencias

- El centro de mando deja de pedir fantasmas y el 404 de manifest/sw desaparece.
- Un `reiniciar` seguido de otro ya no obliga a repetir el comando.
- Sigue en pie: `/pkg/wasm_busqueda.js` dará 404 hasta que se compile el WASM. Es
  esperado, no una regresión, y el log lo dejará ver cada arranque.
