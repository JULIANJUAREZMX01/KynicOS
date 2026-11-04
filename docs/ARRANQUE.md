# Arranque del nodo KYNIKOS — documento único

> Este es el **único** documento oficial de arranque. Si otro archivo copia estos comandos, está mal: debe enlazar aquí.

## La llave maestra

**Windows** — doble clic en `nodo\ARRANCAR.cmd`, o desde PowerShell:

```powershell
cd $HOME\Documents\KynicOS
git pull
.\nodo\kynikos.ps1
```

Sin argumentos ejecuta el flujo completo, verifica cada paso y no repite lo que ya está hecho.

**Linux / macOS** — no es la plataforma del nodo primario. Solo el instalador:

```bash
bash nodo/instalar.sh
```

## Subcomandos

| Comando | Qué hace |
|---|---|
| `kynikos.ps1` | Flujo completo: requisitos, modelo, entorno, config, arranque, validación, tarea |
| `kynikos.ps1 centro` | Abre el menú visual (recomendado si no sabes qué hace falta) |
| `kynikos.ps1 estado` | Modelo, PID, RAM, si escucha Telegram |
| `kynikos.ps1 arrancar` | Solo arranca, sin instalar ni validar |
| `kynikos.ps1 validar` | Comprueba `/api/status` y el polling |
| `kynikos.ps1 detener` | Mata duplicados y libera el puerto 8000 |
| `kynikos.ps1 reparar` | Reinstala dependencias del entorno |
| `kynikos.ps1 configurar` | Reescribe el `.env` y valida el token |
| `kynikos.ps1 doctor` | Hardware y modelo recomendado |
| `kynikos.ps1 logs` | Últimas líneas del registro |
| `kynikos.ps1 tarea` | Arranque automático al iniciar sesión |
| `kynikos.ps1 comandos` | Registra los comandos y la descripción del bot en Telegram |

## Mapa de archivos: qué es y qué no

| Archivo | Estado |
|---|---|
| `nodo/kynikos.ps1` | **CANÓNICO.** Toda la lógica |
| `nodo/ARRANCAR.cmd` | Atajo de doble clic |
| `nodo/CONFIGURAR.cmd` | Atajo de doble clic para el `.env` |
| `nodo/centro.py` | Menú visual. Presenta y delega |
| `nodo/CENTRO.ps1` | Alias: abre el menú |
| `nodo/automatico.ps1` | Alias: flujo completo |
| `nodo/arrancar-y-validar.ps1` | Alias: compatibilidad |
| `nodo/arranque-todo-en-uno.ps1` | Alias: compatibilidad |
| `nodo/asistente-instalacion.ps1` | Alias: compatibilidad |
| `nodo/configurar.ps1` · `instalar.ps1` · `registrar-tarea.ps1` | Alias por subcomando |
| `tools/kynicos.ps1` | Alias: compatibilidad (nombre con errata, no usar) |
| `nodo/instalar.sh` | Solo Linux/macOS. Aborta en Windows |

**Regla:** si un archivo no es `kynikos.ps1` ni `centro.py`, no debe contener lógica de arranque.

## Cuando algo falla

1. Ejecuta `.\nodo\kynikos.ps1 estado` y `.\nodo\kynikos.ps1 doctor`.
2. Mira `kynikos.log` y `kynikos.err.log` en la raíz del repo.
3. Si dudas, `.\nodo\kynikos.ps1 reparar` antes de tocar nada a mano.

Nunca pegues el contenido de un `.ps1` dentro de la consola, ni ejecutes `instalar.sh` en Windows: el primero deja el archivo a medias y el segundo llena la pantalla de errores de sintaxis que no significan nada.
