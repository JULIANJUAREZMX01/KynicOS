# ADR-047 — El nodo arranca sin reimportar su propio módulo

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

En los logs del nodo real cada línea del bloque de arranque salía **dos veces**,
con dos nombres de emisor distintos:

```
INFO | main:<module>:248     - ✅ Chat web registrado en /api/chat
INFO | app.main:<module>:248 - ✅ Chat web registrado en /api/chat
```

La causa está en el cierre de `app/main.py`:

```python
uvicorn.run("app.main:app", ...)
```

Al recibir el nombre como **texto**, uvicorn importa `app.main` otra vez. El
proceso ya lo había ejecutado como `__main__` (`python -m app.main`), así que el
bloque de nivel de módulo corría por segunda vez: se volvían a incluir los
routers y a cargar las personas.

## Decisión

En producción se pasa el **objeto** `app`, no su nombre:

```python
if settings.environment == "development":
    uvicorn.run("app.main:app", ..., reload=True)   # reload exige el texto
else:
    uvicorn.run(app, ..., reload=False)
```

El nombre solo se conserva para `reload`, que es una comodidad de desarrollo y
no lo usa el nodo que corre en la PC.

## Consecuencias

- El bloque de módulo se ejecuta una sola vez en producción: un registro por
  router y una sola carga de personas.
- Se elimina el riesgo de handlers o rutas duplicadas, que con Telegram puede
  significar **responder dos veces al mismo mensaje**.
- Límite de la verificación, dicho claro: el doble import está confirmado por los
  logs del nodo del jefe, pero no pude reproducirlo en el sandbox porque el
  import de `app.channels.web_chat` falla ahí por una dependencia ausente. El
  arreglo es de bajo riesgo y no cambia comportamiento en desarrollo.
