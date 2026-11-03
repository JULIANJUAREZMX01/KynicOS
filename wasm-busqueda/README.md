# Compilar el buscador WASM

Este módulo se compila en una máquina con Rust, no en el servidor. Una vez:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install wasm-pack
cd wasm-busqueda
wasm-pack build --target web --release --out-dir ../web/pkg
```

`wasm-pack` deja `web/pkg/wasm_busqueda_bg.wasm` y su pegamento JS.

La PWA (`web/index.html`) detecta ese paquete al cargar:
- si existe, busca con WASM (más rápido, sin red, 100% en tu equipo);
- si no existe, usa el respaldo en JavaScript con la misma lógica.

Nunca se rompe por no tener el módulo compilado; solo pierde velocidad.
