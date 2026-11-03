# ADR-022 — CLI `kynikos`: instalación configurable por comandos

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Relacionado:** ADR-020 (bot propio), ADR-021 (nodo primario)

## Contexto

La instalación del nodo dependía de leer documentación y copiar comandos a mano. Con tres computadoras disponibles y posiblemente más en el futuro, repetir ese proceso es donde se cometen errores: cada equipo tiene RAM, GPU y sistema operativo distintos, y el modelo que cabe en uno no cabe en otro. El criterio de "modelo más grande posible" tampoco sirve: un modelo que apenas alcanza 1.5 tokens por segundo cabe en memoria y arruina la experiencia.

## Decisión

Un único ejecutable `cli/kynikos.py`, solo biblioteca estándar de Python, que se encarga de la instalación completa y se adapta a cada máquina:

| Comando | Función |
| --- | --- |
| `doctor` | Detecta SO, CPU, RAM total/libre/utilizable, GPU y VRAM, disco, Ollama |
| `plan` | Recomienda modelo y genera el `.env` sugerido sin escribir nada |
| `init` | Escribe `.env` con permisos 600 y token enmascarado |
| `telegram` | Valida el bot, inspecciona el webhook y detecta conflictos con polling |
| `install` | Instala Ollama y dependencias (`--si` para no preguntar) |
| `run` | Arranca el nodo con el entorno cargado |
| `status` | Salud local y modelo configurado |
| `models` | Modelos instalados más la recomendación para ese equipo |
| `config` | Lee o cambia claves del `.env` |
| `service` | Genera unidad systemd o tarea programada de Windows |

### Reglas del planificador

1. Capacidad útil = RAM total menos reserva del sistema operativo (Windows 3.5 GB, macOS 4, Linux 1), o VRAM si hay GPU dedicada.
2. Peso estimado = parámetros × 0.55 GB (Q4_K_M) + 1.2 GB de caché de contexto.
3. **Solo se recomiendan modelos que rindan al menos 4 tokens por segundo.** Por debajo, la conversación se siente rota aunque el modelo quepa. El `doctor` muestra aparte el techo absoluto.
4. Desempate por calidad en español: `qwen2.5` pesa más que `llama` del mismo tamaño porque el bot conversa en español.

### Verificación con tres escenarios

| Equipo | Recomendado | Techo |
| --- | --- | --- |
| 16 GB sin GPU dedicada (patricia73) | `qwen2.5:7b` · 5.3 tok/s | `qwen2.5:14b` · 3.0 tok/s |
| 24 GB de VRAM dedicada | `qwen2.5:32b` · 28.7 tok/s | `qwen2.5:32b` |
| 8 GB de RAM | `qwen2.5:3b` · 9.5 tok/s | `qwen2.5:3b` |

## Hallazgo sobre el bot entregado

El token del bot `kynicOS` corresponde a `@b44_6221857b05e8870c_bot` (id 9085619078) y **es válido**. Pero su webhook ya apunta a `app.base44.com/api/webhooks/telegram/69d1042a619569bfe891119e`, y esa aplicación **no figura** en la lista de apps del propietario: el bot quedó huérfano.

Consecuencia técnica: Telegram permite un solo método de recepción. Mientras ese webhook exista, el nodo propio no puede usar polling (daría conflicto 409). El CLI lo detecta y ofrece salida explícita:

```bash
python3 cli/kynikos.py telegram --liberar
```

No se ejecutó esa liberación sin autorización, porque si esa app existiera en otra cuenta se rompería un servicio ajeno.

## Consecuencias

- Instalar en una computadora nueva es `doctor`, `plan`, `init`, `install`, `telegram`, `run`. Cinco comandos y ninguna decisión a ojo.
- El criterio queda escrito en código, no en la memoria de quien instala: el próximo equipo hereda la misma lógica.
- El planificador es conservador por diseño: prefiere un modelo usable a uno impresionante que tarda ocho minutos en responder.
- Las estimaciones de velocidad son aproximadas (±30%); el comando `status` y las pruebas reales mandan sobre la tabla.
