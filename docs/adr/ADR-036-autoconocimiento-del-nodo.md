# ADR-036 — El nodo conoce su propia configuración

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

Al preguntarle por sus herramientas, conectores, modelo y repositorio, el bot
respondió:

> Mi modelo de lenguaje es Ollama. No tengo acceso a instalaciones locales ni a
> cambios en el sistema operativo. El repositorio único es en GitHub:
> github.com/JAJA-DEV

Las tres afirmaciones son falsas. Ollama es el motor, no el modelo. El nodo sí
tiene acceso al sistema donde corre. Y esa URL de GitHub no existe: el
repositorio es `github.com/JULIANJUAREZMX01/KynicOS`.

El origen es estructural: la persona define quién es el bot en términos de
carácter, pero nada le dice dónde está instalado, qué modelo lo ejecuta ni qué
versión corre. Ante el hueco, el modelo rellena.

## Decisión

1. Nuevo módulo `app/core/autoconocimiento.py` que lee del sistema, en tiempo de
   ejecución: modelo, contexto, motor, proveedores activos, canales, versión de
   Python, SO, núcleos, RAM, rama y commit de git, ruta de instalación y autor.
2. `ConciergeAgentLoop._build_system_prompt` concatena ese bloque al prompt de la
   persona. El modelo deja de adivinar porque tiene el dato delante.
3. Bloque deliberadamente corto (~900 tokens): el nodo trabaja con 4096 de
   contexto y este texto compite con la conversación.
4. Instrucción explícita: si le preguntan algo técnico no cubierto, debe decir
   que no lo tiene verificado. Nunca inventar URLs, versiones ni repositorios.
5. Nuevo comando `/info` que devuelve la misma ficha en formato legible, sin
   pasar por el modelo. Lo que no puede alucinar no se alucina.

## Consecuencias

- Verificado: el prompt contiene el repositorio correcto, el modelo real y el
  commit; `/info` responde con seis comprobaciones en verde y no aparece la URL
  inventada.
- El coste es ~900 tokens de contexto en cada turno. Si el nodo se siente lento,
  este bloque es el primer candidato a recortar, no la persona.
- El bloque se regenera en cada petición, así que refleja un `git pull` o un
  cambio de modelo sin reiniciar nada más que el proceso.
- Limitación conocida: los datos son de la máquina donde corre el proceso, no de
  la máquina del usuario que escribe por Telegram. La ficha describe el nodo.
