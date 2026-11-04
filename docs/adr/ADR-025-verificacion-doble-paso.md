# ADR-025 — Verificación de doble paso para operaciones elevadas

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Módulo:** `app/security/doble_paso.py` · **Pruebas:** `tests/test_doble_paso.py` (25/25)
- **Related:** ADR-021 (nodo primario), ADR-023 (bot `@kynicOS_robot`)

## Contexto

Existía una palabra clave que abría operaciones elevadas en un solo paso. Un solo factor por Telegram es poco: si alguien ve el chat o adivina la frase, ya tiene la puerta abierta. Y el riesgo crecía porque el nodo corre en hardware propio sin la vigilancia de una plataforma.

Se pidió un flujo de doble paso con una condición concreta: tras pronunciar la palabra clave, **una sola** notificación a Telegram pidiendo autorizar, y de esa autorización sale una palabra nueva.

## Decisión

Flujo en dos pasos con confirmación humana:

1. Se pronuncia la palabra del primer paso (`KYNIKOS_PALABRA_1`, leída del entorno, nunca del código).
2. El nodo **no ejecuta nada** y no consulta al modelo: envía una notificación con botones Autorizar y Rechazar.
3. Solo al autorizar se emite una palabra nueva con formato `KALPIXK-XXXX-XXXX`.
4. Esa palabra vale cinco minutos y **un solo uso**. Verificada una vez, muere.

### Reglas que sostienen el diseño

| Regla | Por qué |
| --- | --- |
| Falla cerrado | Sin palabra de primer paso configurada no hay flujo; nunca se busca la clave en otro lado |
| Una sola notificación | Si hay una solicitud pendiente del mismo chat se reutiliza: no se bombardea al usuario |
| Solo hash en disco | La palabra se muestra una vez; después no se puede recuperar del almacenamiento |
| Un solo uso | Reintentar con la misma palabra falla |
| Caducidad | 120 s para autorizar, 300 s de vida de la palabra |
| Freno anti fuerza bruta | Tres fallos bloquean el flujo 15 minutos |
| Persistencia en archivo | En serverless cada petición es un proceso nuevo: sin persistencia el paso 2 no vería al paso 1 |

### Lo que este mecanismo no hace

**No desactiva ningún control de seguridad existente.** Agrega una confirmación humana a operaciones que ya estaban marcadas como elevadas. Un segundo factor que apaga las protecciones no es un segundo factor, es una puerta trasera.

## Verificación

- **Lógica (25 pruebas):** falla cerrado sin configuración, detección tolerante a mayúsculas y espacios, reutilización de solicitud, formato y caducidad de la palabra, un solo uso, rechazo de otro chat, rechazo explícito, solicitud vencida, palabra vencida, bloqueo tras tres fallos, auditoría sin filtrar la palabra.
- **Integración (TestClient, sin red):** la palabra clave crea una solicitud y no llega al modelo; un segundo mensaje no duplica la solicitud; el botón Autorizar emite la palabra; un usuario ajeno no autoriza; un mensaje normal sigue el cauce del modelo.
- **Un bug real encontrado y corregido:** una sustitución automática movió el `return True` fuera de su `if` y la verificación aprobaba cualquier palabra, incluso sin solicitudes. Las pruebas lo detectaron porque comparaban el resultado, no solo el código de estado. Corregido y re-verificado.

## Consecuencias

- El primer factor ya no basta: sin pulsar un botón en Telegram no hay palabra.
- El flujo sobrevive reinicios y despliegues serverless gracias al archivo de estado (`.kynikos/doble_paso.json`).
- El costo es fricción: dos pasos y una espera de hasta dos minutos. Es el precio correcto para operaciones elevadas, no para el chat normal.
- Queda configurable desde el CLI: `kynikos doble-paso estado|solicitar|verificar`.
