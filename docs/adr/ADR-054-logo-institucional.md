# ADR-054: Logo institucional en el repositorio

## Contexto
El 7-nov Julián entregó el logo oficial de UNT (rinoceronte sobre placa de
circuito, paleta verde y turquesa). El JPG venía con fondo celeste plano, que
sobre el README blanco queda como un recuadro ajeno a la página.

## Decisión
- Original en `docs/assets/unt-logo.jpg` y copia en `public/brand/` (la que usan
  web y PWA), sin modificar el arte.
- Versión con el fondo recortado: `docs/assets/unt-logo.png` (685×685, alfa) y
  `public/brand/unt-logo-256.png` para la interfaz. El recorte elimina solo el
  celeste del fondo por distancia de color; el blanco del rinoceronte y de las
  letras se conserva.
- El logo encabeza `docs/PUBLICO.md` y `README.md`.

## Observaciones para Julián, no corregidas aquí
1. El texto perimetral parece decir "ENGIINERRING" y "DEVELOPENT". Si se
   confirma, es erratas visibles en la pieza pública; el arte no se toca sin su
   visto bueno.
2. El logo dice "UNITED NORTH TEAM"; la marca que usamos en servicios es "UNT
   Tecnologías Computacionales Cancún". Conviene decidir cuál manda en contextos
   públicos y si el logo lleva el nombre largo en algún soporte.
3. El texto curvado de la parte superior se lee como relleno ilegible; si es
   intencional, se respeta, pero no comunica.

## Consecuencias
- Cualquier soporte nuevo reutiliza `unt-logo-256.png` en vez de recortar el JPG
  a mano.
- Si Julián entrega un SVG, se sustituye y este ADR se actualiza.
