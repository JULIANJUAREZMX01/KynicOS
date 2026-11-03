# Agentes en KynicOS — llave de Jules y estándar

- **Fecha:** 2026-11-03 · **Estándar canónico:** `docs/ESTANDAR-REPOS.md` en `JULIANJUAREZMX01/JULIANJUAREZMX01.github.io`

## 1. Reglas que aplican aquí

Este repositorio sigue el estándar modular v1.0. Las reglas relevantes para agentes:

| ID | Regla |
| --- | --- |
| AGT-01 | `AGENTS.md` con las ocho secciones fijas (ya cumple) |
| AGT-02 | `CLAUDE.md` y `GEMINI.md` son punteros, no copias |
| AGT-03 | Un máximo de un PR abierto por agente. Sin auto-merge |
| AGT-04 | Cada aprendizaje entra en `docs/agentes/MEMORIA.md` con medición |
| SEC-02 | Las llaves viven en GitHub Actions secrets, nunca en el código |

## 2. Llave de Jules en este repositorio

- **Nombre del secreto:** `JULES_API_KEY`
- **Dónde vive:** GitHub Actions secrets de este repo y gestor de secretos del agente. Aplicado el 2026-11-03 (respuesta 201 de GitHub).
- **Cómo se usa:** `${{ secrets.JULES_API_KEY }}` en el workflow, y `JULES_API_KEY` en el `.env` local. El valor nunca se escribe en un archivo del repositorio.
- **Formato:** la llave de Google lleva prefijo `AQ.` y mide 53 caracteres. Si al leerla mide 50, le falta el prefijo y la API devolverá 401 (SEC-04).
- **Rotación:** nuevo valor en el gestor, propagar con la función `githubSetSecret`, revocar el anterior (SEC-03).

## 3. Pendientes de este repo

1. `KynicOS Tests` lleva fallas seguidas: mientras siga rojo, CI-01 no se cumple.
2. El despliegue en Render está suspendido por facturación: lo estático migra a Pages (ADR-006).
3. El bucle de entrenamiento descrito en `docs/ESTADO-ACTUAL.md` no arranca hasta que el CI esté en verde.
