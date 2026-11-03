# ADR-021 — KYNIKOS como nodo primario: PC propia, tokens ilimitados y consola web con WASM

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada (núcleo implementado, activación pendiente de token y equipo)
- **Relacionado:** ADR-020 (KYNIKOS deja de ser concierge)

## Contexto

ADR-020 dejó a KYNIKOS como bot propio con dos caminos de despliegue. Julián amplía el objetivo: no quiere un bot prestado, quiere **su bot** corriendo en una de sus tres computadoras, con modelo local para no tener techo de tokens, disponible por web con herramientas WASM, conectado a los MCP del ecosistema, y como pieza central de la arquitectura. Base44 (este agente) pasa a ser el coordinador, no el único cerebro.

La intención explícita: "que se supere a sí mismo y a todas sus versiones anteriores". Eso exige tres cosas que un chatbot no tiene: memoria persistente, registro de sus propios errores y capacidad de cambiar su propio contexto sin que se lo dicten.

## Arquitectura decidida

Cuatro capas, de dentro hacia fuera:

1. **Nodo local (la PC).** Python + KynicOS + Ollama. Es el cerebro cotidiano. Atiende Telegram por polling (no necesita URL pública) y expone HTTP en la red local. Coste por token: cero. Velocidad: la del equipo.
2. **Consola web (PWA estática).** Servida desde GitHub Pages, sin costo ni servidor. Chat contra el nodo, histórico en IndexedDB del propio navegador y búsqueda local con **WASM**. Funciona sin conexión para leer el histórico; con nodo encendido, conversa.
3. **Capa MCP.** `mcp-servers.json` declara las herramientas disponibles: Context7 para documentación, y cuatro internas del nodo (búsqueda web sin API key, lectura de archivos acotada al workspace, ejecución local con el ejecutor endurecido `shell=False`, y memoria persistente). Las llaves viven en `.env`, nunca en el manifiesto.
4. **Orquestador Base44 (yo).** Tareas que exceden al modelo modesto: investigación con conectores, escritura en repositorios, análisis largo, coordinación con personas. Aquí sí se consumen créditos.

## Modelo de créditos (sin adornos)

- El nodo local **no consume créditos de Base44**. Hablar con él es gratis después de la inversión de hardware.
- Los créditos se gastan **cuando trabajo yo**: sesiones de análisis, deploys, investigación, escritura en repos.
- Consecuencia práctica: si todo el tráfico cotidiano se enruta al nodo local, el crédito disponible rinde mucho más porque se reserva a lo complejo. Lo contrario, automatizar cada mensaje contra Base44, lo agota.
- No existe "crédito ilimitado" en ninguna capa: el nodo evita el coste por token, no el consumo eléctrico ni el desgaste del equipo.

## Autosuperación: cómo se implementa sin misticismo

1. **Memoria doble.** Histórico de conversación en IndexedDB (navegador) + `read_nanobot_memory` en el nodo. El contexto sobrevive a reinicios.
2. **Bitácora de errores.** Cada fallo del nodo se registra con tipo y causa. Un turno de revisión periódica lee esa bitácora y propone ajustes al `system_prompt` o a las herramientas.
3. **Regla de no repetir.** El nodo consulta `docs/agentes/MEMORIA.md` antes de responder sobre trabajo previo, igual que los agentes de repositorio.
4. **Evaluación.** Cada N turnos, el nodo resume qué respondió mal y qué regla lo habría evitado. Ese resumen es el insumo para la siguiente versión del prompt. Sin este paso, "superarse" es una frase de mercadotecnia.

## Verificado en este turno

| Pieza | Comprobación |
| --- | --- |
| `POST /api/chat` | 200; responde error accionable cuando ningún proveedor está disponible |
| `GET /api/chat/historial` y `/reiniciar` | 200, gestión de turnos correcta |
| `GET /api/telegram` (webhook) + `/salud` | 200, valida secreto y usuario autorizado |
| MCP ampliado | 11 herramientas expuestas, incluidas `buscar_web`, `leer_archivo`, `ejecutar_comando`, `listar_mcp` |
| `mcp-servers.json` | Válido, 5 servidores declarados |
| PWA `web/index.html`, `sw.js`, `manifest` | Sintaxis JS/JSON validada, Service Worker con shell offline |
| Crate `wasm-busqueda` | Rust + wasm-bindgen listo; se compila en la PC (`wasm-pack`) |
| `nodo/instalar.sh` | Sintaxis bash válida; instala Ollama, venv, deps y deja `.env` plantilla |

## Límites honestos

- **No puedo levantar el servicio yo**: no tengo acceso a tus tres computadoras ni al token de BotFather. Entrego el instalador de un comando; la ejecución es tuya.
- **El sandbox no configura accesos remotos.** La exposición del nodo fuera de la red local (para abrir la consola desde el móvil con datos) se resuelve en tu equipo con la herramienta que prefieras; queda documentado, no ejecutado.
- **Un modelo modesto razona menos.** Para código fino o análisis largo, el nodo debe delegar en mí. La arquitectura está pensada para esa división del trabajo, no para fingir que un 7B hace lo mismo que un modelo grande.
- **Un solo nodo activo a la vez.** Tres equipos disponibles no significan tres cerebros: con memoria separada se contradicen. Se elige un nodo primario; los otros pueden ser respaldo frío.
- **WASM compila en tu máquina.** Aquí no hay Rust; la PWA detecta el módulo si existe y cae a JavaScript si no. Nunca se rompe, solo pierde velocidad.

## Pendientes para activar

1. Token del bot desde BotFather.
2. Elegir cuál de las tres PC será el nodo primario (la de más RAM, encendida de día).
3. Ejecutar `bash nodo/instalar.sh`, editar `.env`, arrancar.
4. Compilar el WASM (`wasm-pack build`) la primera vez.
5. Publicar la consola en GitHub Pages y apuntarla a la URL del nodo.
