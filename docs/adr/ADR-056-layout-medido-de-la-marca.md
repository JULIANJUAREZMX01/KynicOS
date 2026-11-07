# ADR-056: Layout medido y verificado para la marca JAJA.DEV

## Contexto
La primera versión (ADR-055) salió con dos defectos, ambos de composición y no
del generador de imágenes:

1. **Texto desbordado.** El lema se dibujó como `S O F T W A R E   ·   S E C U R I T Y…`
   con espacios dobles entre letras: medía ~1240 px sobre un lienzo de 1080, así
   que se cortaba en ambos bordes.
2. **Solape.** En el video el emblema escalaba hasta y=580 mientras el nombre se
   dibujaba centrado en y=570: se pisaban durante toda la animación.

La causa común: posiciones y tamaños escritos a mano, sin comprobar el resultado.

## Decisión
`docs/assets/jaja-dev/marca.py` centraliza la composición y **hace cumplir** tres
reglas, elevando error si alguna falla:

- Ninguna línea excede el 86% del ancho del lienzo: la fuente se reduce de 1 en 1
  píxel hasta que cabe (`ajustar()`).
- El bloque de texto no se solapa con el emblema: se comparan las cajas reales.
- Nada se sale por los márgenes laterales ni por abajo.

El lema se escribe normal (`SOFTWARE · SECURITY · AUTOMATION`) y el espaciado lo
resuelve la tipografía, no espacios manuales.

El video reutiliza ese layout: el emblema termina en 502 px y el nombre arranca en
609 px sobre 810, con un `assert` que lo verifica antes de renderizar.

## Consecuencias
- Verificado en la corrida real: emblema 669 px, nombre 750-874, lema 980-1018 con
  791 px de ancho sobre 928 disponibles. Cero solapes, cero desbordes.
- Cambiar el lema o el nombre no rompe nada: se reajusta solo.
- Quien edite la marca ya no necesita medir a ojo; el script lo rechaza.
