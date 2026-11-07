# ADR-060: Imports faltantes en loop.py, y por qué la suite no lo vio

## Contexto
Tras ADR-056 (`_max_salida`) y ADR-052 (medición de tiempo), todo mensaje libre
de Telegram fallaba con `name 'os' is not defined` en `app/core/loop.py:84`. El
bot respondía, pero con el aviso genérico de error en vez de la respuesta real.

Causa: el parche que introdujo `_max_salida()` añadía los imports con esta guarda:

```python
if "import os" not in s.split("class ")[0]:
    s = s.replace("import logging", "import logging\nimport os\nimport time", 1)
```

`loop.py` no usa `import logging` sino `from app.utils import get_logger`, así que
el reemplazo no encontró nada, **no falló** y el archivo quedó usando `os` y `time`
sin importarlos. El `replace` silencioso es la trampa: no avisa cuando no aplica.

## Por qué las 49 pruebas no lo detectaron
Ninguna ejecuta `process_message`, que es donde se tocan `os.getenv` y
`time.monotonic`. La suite cubre otras capas. Un import faltante en una ruta no
ejercitada es invisible por muy verde que esté todo.

## Decisión
- Añadir `import os` e `import time` en la cabecera real del archivo.
- Verificar con una prueba que **instancia** el loop y llama a `_max_salida()`, no
  solo que el módulo importe. Importar un módulo no ejecuta sus métodos.
- Regla para los parches: un `replace` debe ir acompañado de `assert`, o de un
  `if` que verifique el resultado, nunca de una condición que pueda no cumplirse
  en silencio.

## Consecuencias
- Verificado: `_max_salida()` devuelve 320 y `time.monotonic()` responde.
- 49 pruebas verdes.
- Queda pendiente (recomendado): una prueba que ejercite `process_message` con un
  proveedor falso, para que esta clase de fallo salte en CI y no en producción.
