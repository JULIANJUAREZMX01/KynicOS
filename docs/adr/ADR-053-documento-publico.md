# ADR-053: Documento de presentación pública

## Contexto
El README y los ADRs están escritos para quien opera y modifica el nodo: commits,
PIDs, tokens, rutas internas. Sirven para trabajar, no para presentar. Hacía falta
una pieza que explique el proyecto a alguien de fuera sin exponer detalles
operativos ni prometer lo que el sistema no hace.

## Decisión
`docs/PUBLICO.md`: presentación en lenguaje llano, con la arquitectura por capas
explicada sin jerga, las capacidades reales de hoy y una sección explícita de
límites (corre en una PC, ~4 tokens/s sin GPU, un solo dueño, no es producto
terminado).

Se excluye deliberadamente: tokens, IDs de chat, nombres de archivos internos de
arranque, números de versión y cualquier detalle que facilite un ataque o que se
rompa con el siguiente commit.

## Consecuencias
- Sirve para clientes, aliados y colaboradores sin adaptar nada.
- Los límites declarados son verificables; si el rendimiento mejora (GPU, modelo
  menor) esta página debe actualizarse para no quedarse corta.
- No sustituye al README: el README sigue siendo la referencia técnica.
