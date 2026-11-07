# ADR-055: Marca personal JAJA.DEV

## Contexto
Julián pidió una pieza de marca personal con el mismo lenguaje que el logo de UNT
(insignia circular, placa de circuito, paleta verde), pero para su identidad de
desarrollador: `jaja.dev`, firma que ya usa en GitHub y LinkedIn.

El logo de UNT tiene dos problemas que no se repiten aquí: el texto perimetral
trae erratas (`ENGIINERRING`, `DEVELOPENT`) y letras ilegibles generadas por IA.

## Decisión
- **Emblema generado sin texto**. El modelo solo produce el símbolo: cabeza de
  lobo guardián geométrica sobre trazas de circuito, esmeralda y turquesa. Los
  modelos escriben mal, así que no se les pide escribir.
- **Tipografía compuesta por código** (`Pillow`): `JAJA.DEV` con DejaVu Sans Bold
  y el lema `SOFTWARE · SECURITY · AUTOMATION`. Cero erratas posibles.
- **Video generado con fotogramas reales**, no una plantilla: 180 frames a 30 fps,
  emblema con zoom y fundido, barrido de luz vertical sobre el circuito,
  aparición del nombre y del lema, halo que respira. MP4 1080×1080 y GIF.
- Todo reproducible: `docs/assets/jaja-dev/componer.py` y `video.py` regeneran
  la pieza; cambiar el color o el lema es editar una línea.

## Consecuencias
- La marca personal queda separada de la de UNT pero comparte familia visual.
- Al ser generado por script, cualquier ajuste (paleta, lema, duración) se aplica
  sin volver a pasar por un generador de imágenes.
- El emblema es una interpretación generada por IA: si Julián quiere un símbolo
  dibujado a mano, se sustituye `emblema-fuente.png` y se vuelve a correr el
  script. Nada más cambia.
