# ADR-059: Inventario completo del ecosistema

## Contexto
`app/core/ecosystem.py` registraba solo 4 repositorios: kynicos, kalpixk,
kynykos_ai_agent y orquestador. Faltaban los del trabajo diario, así que
`/ecosistema` daba una foto incompleta y `/ecosistema_buscar` no podía encontrar
nada en ellos.

## Decisión
Se añaden cinco repositorios con su rol y lo que aportan al conjunto:

| clave | repo | rol |
|---|---|---|
| muevecancun | JULIANJUAREZMX01/MueveCancun | producto |
| cantabria | JULIANJUAREZMX01/cantabria-pms-demo | operación |
| nanobot | JULIANJUAREZMX01/nanobot-cloud | nube |
| portafolio | sistemascancunjefe-ai/Portfolio_JAJA_DEV | marca |
| sanaciones | JULIANJUAREZMX01/sanaciones-cuanticas | media |

Cada entrada lleva varias `carpetas` candidatas porque el nombre de la carpeta
local no siempre coincide con el del repo, y un campo `aporta` que describe para
qué sirve dentro del ecosistema, no solo dónde está.

## Consecuencias
- `/ecosistema` pasa de 4 a 9 repositorios; los ausentes se listan con su URL en
  vez de omitirse, que es información útil.
- `portafolio` vive en otra organización (`sistemascancunjefe-ai`), no en la
  cuenta personal: queda registrado así para no confundirlo.
- Verificado: `inventario()` resuelve 6 de 9 en el sandbox y `estado()` los
  clasifica bien entre presentes y ausentes.
- Añadir un repo nuevo es editar `REPOS`; no hace falta tocar los comandos.
