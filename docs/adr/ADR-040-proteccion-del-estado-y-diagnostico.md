# ADR-040 — El estado se cierra con token y el bot diagnostica sus registros

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Cierra el riesgo abierto en ADR-032**

## Contexto

Dos deudas de fondo, ambas señaladas el 4-nov y aplazadas por incendios:

**1. `/api/status` no exigía autenticación.** Devolvía PID, persona, si el token
de Telegram estaba cargado, skills y URL de despliegue a cualquiera que acertara
la URL. ADR-032 lo dejó condicionado: no abrir el túnel ni exponer el nodo hasta
protegerlo. Y con un túnel delante, la petición llega desde `127.0.0.1`, así que
filtrar por IP de origen no sirve.

**2. No existía instalación guiada.** El bot sabía decir `/estado` y `/logs`, pero
no en qué paso había fallado un arranque. La noche del 6-nov el diagnóstico lo
hizo una persona leyendo pantallas durante dos horas; todos los fallos estaban en
el registro y todos tenían causa reconocible.

## Decisión

### Estado protegido, fallando cerrado

1. `/api/health` es público y devuelve solo `{"ok": true, "service": "kynikos"}`:
   un latido para monitores y túneles, sin un solo dato del nodo.
2. `/api/status` exige `KYNIKOS_API_TOKEN`, por cabecera `X-Kynikos-Token` o por
   `?token=`.
3. **Si no hay token configurado, responde 503**, no 200. Falla cerrado: el
   olvido no abre la puerta, la cierra.
4. La comparación usa `secrets.compare_digest`, en tiempo constante.
5. El token se genera solo al configurar el nodo (24 bytes aleatorios, 48
   caracteres hex) y se guarda en `.env`. `.env.example` documenta el campo.
6. `kynikos.ps1 api` consulta el estado con el token del `.env` sin exponerlo en
   la línea de comandos.

### Diagnóstico determinista

1. Nuevo `app/core/diagnostico.py`: lee `kynikos.err.log` y `kynikos.log` y
   reconoce ocho fallos con título, causa y remedio.
2. Los patrones salen de fallos reales: dependencia ausente, puerto ocupado,
   doble instancia, token rechazado, Ollama caído, memoria insuficiente, error de
   codificación en consola Windows y error de sintaxis.
3. **No usa el modelo.** Un diagnóstico determinista no puede alucinar.
4. Nuevo comando `/instalar` en el bot, registrado en el menú de Telegram.

## Consecuencias

- Verificado con seis peticiones reales: health 200 sin token, status 401 sin
  token y con token erróneo, 200 con token por cabecera y por query, y 503 cuando
  no hay token configurado.
- Verificado el diagnóstico con los cinco fallos de la noche: detecta los cinco y
  no inventa ninguno con un registro sano. Nueve pruebas nuevas; suite en 49.
- Ya se puede abrir el túnel sin dejar el nodo a la vista, que era la condición
  de ADR-032. Queda pendiente proteger también la PWA si se expone.
- Limitación conocida: los patrones son finitos. Un fallo nuevo dará "sin fallos
  conocidos" y mostrará las últimas líneas; entonces se añade el patrón.
