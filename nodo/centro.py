#!/usr/bin/env python3
"""KYNIKOS · Centro de comando del nodo.

Un solo programa, sin dependencias: menú con flechas para todo lo que antes
estaba repartido en seis scripts de PowerShell.

  estado      PID, puerto, polling y modelo, leídos del proceso real
  arrancar    igual que cli\\kynikos.py run, en segundo plano y con logs
  detener     mata al dueño del puerto, no a cualquier python
  reiniciar   detener + arrancar + esperar a que levante
  logs        últimas líneas y seguimiento en vivo
  configurar  token, modelo, puerto y raíces del ecosistema en .env
  requisitos  git, python, ollama, modelo descargado y dependencias
  reparar     duplicados, puerto ocupado y procesos huérfanos
  reporte     resumen en texto y JSON

Uso:
    .\\nodo\\CENTRO.cmd          (doble clic o desde PowerShell)
    python nodo\\centro.py

Teclas: flechas para moverse, Enter para elegir, q para salir.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NODO = RAIZ / "nodo"
ESTADO_DIR = RAIZ / ".kynikos"
PID_FILE = ESTADO_DIR / "nodo.pid"
LOG = RAIZ / "kynikos.log"
ERR = RAIZ / "kynikos.err.log"
ENV = RAIZ / ".env"

ANCHO = 64


# ── utilidades de consola ────────────────────────────────────────────────────

class Color:
    ok = "\033[92m"
    mal = "\033[91m"
    aviso = "\033[93m"
    gris = "\033[90m"
    titulo = "\033[96m"
    sel = "\033[7m"
    fin = "\033[0m"


def _habilitar_ansi() -> None:
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


def limpiar() -> None:
    print("\033[2J\033[H", end="")


def bien(t: str) -> None:
    print(f"  {Color.ok}OK{Color.fin}    {t}")


def mal(t: str) -> None:
    print(f"  {Color.mal}FALLO{Color.fin} {t}")


def aviso(t: str) -> None:
    print(f"  {Color.aviso}AVISO{Color.fin} {t}")


def gris(t: str) -> None:
    print(f"  {Color.gris}{t}{Color.fin}")


# ── lectura de configuración ────────────────────────────────────────────────

def leer_env() -> dict[str, str]:
    datos: dict[str, str] = {}
    if ENV.exists():
        for linea in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            datos[clave.strip()] = valor.strip().strip('"').strip("'")
    return datos


def _delegar(accion: str) -> bool:
    """Pasa la accion a la llave maestra (nodo\\kynikos.ps1, ADR-031).

    El centro decide QUE hacer; como hacerlo vive solo en el orquestador.
    Devuelve False en Linux o si el orquestador no esta, para que la logica
    local siga sirviendo de respaldo.
    """
    if os.name != "nt":
        return False
    ps1 = RAIZ / "nodo" / "kynikos.ps1"
    if not ps1.exists():
        return False
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), accion],
            cwd=str(RAIZ),
        )
        return True
    except Exception:
        return False


def puerto_nodo() -> int:
    for clave in ("KYNIKOS_PORT", "PORT"):
        valor = os.environ.get(clave) or leer_env().get(clave, "")
        if valor.isdigit():
            return int(valor)
    return 8000


def python_venv() -> Path:
    candidatos = [
        NODO / ".venv" / "Scripts" / "python.exe",
        NODO / ".venv" / "bin" / "python",
        RAIZ / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidatos:
        if c.exists():
            return c
    return Path(sys.executable)


# ── detección del proceso real ──────────────────────────────────────────────

def pids_en_puerto(puerto: int) -> list[int]:
    """Dueños del puerto según netstat.

    No se usa Get-NetTCPConnection: si el módulo NetTCPIP falla, devuelve vacío
    en silencio y el nodo parece caído aunque esté escuchando. Ese falso
    negativo fue el que dejó a Julián con "FALLO el nodo no esta escuchando"
    mientras uvicorn decía "Uvicorn running on http://0.0.0.0:8000".
    """
    ids: list[int] = []
    try:
        salida = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                timeout=15, errors="replace").stdout
    except Exception:
        return ids
    patron = re.compile(rf"[:.]{puerto}\s+\S+\s+LISTENING\s+(\d+)", re.IGNORECASE)
    for linea in salida.splitlines():
        m = patron.search(linea)
        if m:
            ids.append(int(m.group(1)))
    return sorted(set(ids))


def puerto_abierto(puerto: int) -> bool:
    for host in ("127.0.0.1", "::1"):
        familia = socket.AF_INET6 if ":" in host else socket.AF_INET
        try:
            with socket.socket(familia, socket.SOCK_STREAM) as s:
                s.settimeout(0.6)
                if s.connect_ex((host, puerto)) == 0:
                    return True
        except OSError:
            continue
    return False


def polling_activo() -> bool:
    """La señal buena: la línea de polling del bot en el log reciente."""
    if not LOG.exists():
        return False
    try:
        lineas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-250:]
    except OSError:
        return False
    texto = "\n".join(lineas).lower()
    if "unauthorized" in texto or "conflict" in texto:
        return False
    return "polling started" in texto or "polling: activo" in texto


def modelo_activo() -> str:
    env = leer_env()
    return env.get("OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL") or "qwen2.5:7b"


def arranque_hace() -> str:
    """Cuánto lleva vivo el proceso dueño del puerto."""
    ids = pids_en_puerto(puerto_nodo())
    if not ids:
        return "sin proceso"
    if os.name != "nt":
        return "activo"
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-Process -Id {ids[0]} -ErrorAction SilentlyContinue).StartTime"],
            capture_output=True, text=True, timeout=20)
        bruto = ps.stdout.strip()
        if not bruto:
            return "activo"
        import datetime as _dt
        inicio = _dt.datetime.strptime(bruto[:19], "%d/%m/%Y %H:%M:%S") \
            if "/" in bruto else _dt.datetime.fromisoformat(bruto[:19])
        minutos = int((_dt.datetime.now() - inicio).total_seconds() // 60)
        return f"{minutos} min" if minutos >= 0 else "activo"
    except Exception:
        return "activo"


def nodo_vivo() -> bool:
    return bool(pids_en_puerto(puerto_nodo())) or puerto_abierto(puerto_nodo())


# ── acciones ────────────────────────────────────────────────────────────────

def accion_estado() -> None:
    if _delegar("estado"):
        return
    puerto = puerto_nodo()
    ids = pids_en_puerto(puerto)
    print()
    if ids and puerto_abierto(puerto):
        bien(f"nodo escuchando en el puerto {puerto} (PID {', '.join(map(str, ids))})")
    elif ids:
        aviso(f"proceso en el puerto {puerto} (PID {ids[0]}), pero no acepta conexiones")
    else:
        mal(f"no hay nada escuchando en el puerto {puerto}")
    print()
    gris(f"modelo      {modelo_activo()}")
    gris(f"encendido   {arranque_hace()}")
    gris(f"polling     {'activo' if polling_activo() else 'sin señal en el log'}")
    gris(f"python      {python_venv()}")
    gris(f"log         {LOG}")
    if not polling_activo() and LOG.exists():
        print()
        aviso("mira las últimas líneas con la opción Logs")


def accion_arrancar() -> None:
    if _delegar("arrancar"):
        return
    puerto = puerto_nodo()
    print()
    if nodo_vivo():
        bien(f"ya estaba corriendo en el puerto {puerto}; no se duplica")
        return
    py = python_venv()
    if not py.exists():
        mal("no encuentro el python del entorno; corre antes la opción Requisitos")
        return
    ESTADO_DIR.mkdir(exist_ok=True)
    log = LOG.open("a", encoding="utf-8", errors="replace")
    err = ERR.open("a", encoding="utf-8", errors="replace")
    comando = [str(py), str(RAIZ / "cli" / "kynikos.py"), "run"]
    banderas = 0
    if os.name == "nt":
        banderas = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    try:
        proc = subprocess.Popen(comando, cwd=str(RAIZ), stdout=log, stderr=err,
                                stdin=subprocess.DEVNULL, creationflags=banderas)
    except Exception as e:
        mal(f"no pude lanzarlo: {e}")
        return
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    aviso(f"lanzado con PID {proc.pid}; el modelo tarda en cargar")
    for i in range(1, 13):
        time.sleep(2)
        if puerto_abierto(puerto):
            bien(f"puerto {puerto} escuchando tras {i * 2} s")
            if polling_activo():
                bien("polling de Telegram activo")
            else:
                aviso("el puerto responde; el polling tarda un poco más")
            return
        print(f"  {Color.gris}esperando... {i * 2} s{Color.fin}")
    mal("no abrió el puerto en 24 s; revisa Logs")


def accion_detener() -> None:
    if _delegar("detener"):
        return
    puerto = puerto_nodo()
    ids = pids_en_puerto(puerto)
    print()
    if not ids:
        bien("no había nada corriendo")
        return
    for pid in ids:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"] if os.name == "nt"
                           else ["kill", "-9", str(pid)],
                           capture_output=True, timeout=15)
            bien(f"detenido PID {pid}")
        except Exception as e:
            mal(f"no pude detener {pid}: {e}")
    for _ in range(10):
        if not puerto_abierto(puerto):
            break
        time.sleep(0.5)


def accion_reiniciar() -> None:
    accion_detener()
    time.sleep(1)
    accion_arrancar()


def accion_logs() -> None:
    if _delegar("logs"):
        return
    print()
    if not LOG.exists():
        mal("todavía no hay kynikos.log")
        return
    lineas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"  {Color.gris}últimas {min(40, len(lineas))} líneas{Color.fin}")
    for l in lineas[-40:]:
        print(f"  {l}")
    print()
    gris("Ctrl+C para volver al menú")
    try:
        with LOG.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            while True:
                nueva = f.readline()
                if nueva:
                    print(f"  {nueva.rstrip()}")
                else:
                    time.sleep(0.7)
    except KeyboardInterrupt:
        return


def accion_configurar() -> None:
    if _delegar("configurar"):
        return
    env = leer_env()
    print()
    gris("Enter deja el valor actual. Los valores no se muestran completos.")
    cambios: dict[str, str] = {}

    actual = env.get("TELEGRAM_TOKEN", "")
    pista = f"{actual[:6]}...{actual[-4:]}" if len(actual) > 12 else ("vacío" if not actual else "corto")
    valor = input(f"  TELEGRAM_TOKEN [{pista}]: ").strip()
    if valor:
        cambios["TELEGRAM_TOKEN"] = valor

    valor = input(f"  OLLAMA_MODEL [{env.get('OLLAMA_MODEL', 'qwen2.5:7b')}]: ").strip()
    if valor:
        cambios["OLLAMA_MODEL"] = valor

    valor = input(f"  KYNIKOS_PORT [{env.get('KYNIKOS_PORT', '8000')}]: ").strip()
    if valor.isdigit():
        cambios["KYNIKOS_PORT"] = valor

    valor = input(f"  KYNIKOS_ECOSYSTEM_ROOTS [{env.get('KYNIKOS_ECOSYSTEM_ROOTS', '')}]: ").strip()
    if valor:
        cambios["KYNIKOS_ECOSYSTEM_ROOTS"] = valor

    if not cambios:
        bien("sin cambios")
        return
    lineas = ENV.read_text(encoding="utf-8", errors="replace").splitlines() if ENV.exists() else []
    if ENV.exists():
        respaldo = ENV.with_suffix(".env.respaldo")
        respaldo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        gris(f"respaldo en {respaldo.name}")
    puestas: set[str] = set()
    salida: list[str] = []
    for linea in lineas:
        clave = linea.split("=", 1)[0].strip() if "=" in linea and not linea.strip().startswith("#") else None
        if clave in cambios:
            salida.append(f"{clave}={cambios[clave]}")
            puestas.add(clave)
        else:
            salida.append(linea)
    for clave, valor in cambios.items():
        if clave not in puestas:
            salida.append(f"{clave}={valor}")
    ENV.write_text("\n".join(salida) + "\n", encoding="utf-8")
    bien(f"guardado en .env: {', '.join(cambios)}")
    aviso("para que tome efecto: Reiniciar")


def accion_requisitos() -> None:
    print()
    for nombre, comando in (("git", ["git", "--version"]),
                            ("python", [str(python_venv()), "--version"]),
                            ("ollama", ["ollama", "--version"])):
        try:
            r = subprocess.run(comando, capture_output=True, text=True, timeout=25)
            if r.returncode == 0:
                bien(f"{nombre}: {(r.stdout or r.stderr).strip().splitlines()[0]}")
            else:
                mal(f"{nombre} responde con error")
        except FileNotFoundError:
            mal(f"{nombre} no está en el PATH")
        except Exception as e:
            mal(f"{nombre}: {e}")
    modelo = modelo_activo()
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
        if modelo.split(":")[0] in r.stdout:
            bien(f"modelo {modelo} descargado")
        else:
            aviso(f"modelo {modelo} no aparece en ollama list")
    except Exception:
        aviso("no pude consultar ollama list")
    try:
        r = subprocess.run([str(python_venv()), "-c", "import telegram, loguru, httpx; print('ok')"],
                           capture_output=True, text=True, timeout=30)
        if "ok" in r.stdout:
            bien("dependencias: telegram, loguru, httpx")
        else:
            mal("faltan dependencias; corre la instalación")
    except Exception as e:
        mal(f"no pude comprobar dependencias: {e}")


def accion_reparar() -> None:
    if _delegar("reparar"):
        return
    puerto = puerto_nodo()
    print()
    ids = pids_en_puerto(puerto)
    if len(ids) > 1:
        aviso(f"hay {len(ids)} procesos en el puerto {puerto}: {ids}; dejo el más antiguo")
        for pid in ids[1:]:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"] if os.name == "nt"
                           else ["kill", "-9", str(pid)], capture_output=True)
    elif ids:
        bien(f"un solo dueño del puerto {puerto}: PID {ids[0]}")
    else:
        bien(f"puerto {puerto} libre")
    huerfanos: list[int] = []
    if os.name == "nt":
        try:
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                 "Where-Object { $_.CommandLine -like '*kynikos.py*run*' }).ProcessId"],
                capture_output=True, text=True, timeout=40)
            huerfanos = [int(x) for x in ps.stdout.split() if x.strip().isdigit()]
        except Exception:
            pass
    sobrantes = [p for p in huerfanos if p not in ids]
    if sobrantes:
        aviso(f"procesos del nodo sin puerto asignado: {sobrantes}; los cierro")
        for pid in sobrantes:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        bien("sin procesos huérfanos del nodo")
    if not LOG.exists():
        aviso("no hay kynikos.log; el nodo nunca arrancó aquí")


def accion_reporte() -> None:
    puerto = puerto_nodo()
    datos = {
        "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repo": str(RAIZ),
        "puerto": puerto,
        "pids": pids_en_puerto(puerto),
        "escuchando": puerto_abierto(puerto),
        "polling": polling_activo(),
        "modelo": modelo_activo(),
        "encendido": arranque_hace(),
        "python": str(python_venv()),
        "log": str(LOG),
        "log_existe": LOG.exists(),
    }
    print()
    for clave, valor in datos.items():
        print(f"  {clave:<14} {valor}")
    ESTADO_DIR.mkdir(exist_ok=True)
    salida = ESTADO_DIR / "reporte.json"
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    gris(f"guardado en {salida}")


OPCIONES = [
    ("Estado del nodo", accion_estado),
    ("Arrancar", accion_arrancar),
    ("Detener", accion_detener),
    ("Reiniciar", accion_reiniciar),
    ("Logs", accion_logs),
    ("Configurar", accion_configurar),
    ("Requisitos", accion_requisitos),
    ("Reparar", accion_reparar),
    ("Reporte", accion_reporte),
    ("Salir", None),
]


# ── menú ────────────────────────────────────────────────────────────────────

def _leer_tecla() -> str:
    """Devuelve 'arriba', 'abajo', 'enter', 'q' o el carácter pulsado."""
    if os.name == "nt":
        import msvcrt
        t = msvcrt.getch()
        if t in (b"\xe0", b"\x00"):
            t2 = msvcrt.getch()
            return {"H": "arriba", "P": "abajo"}.get(t2.decode(errors="ignore"), "")
        if t in (b"\r", b"\n"):
            return "enter"
        return t.decode(errors="ignore").lower()
    import termios
    import tty
    fd = sys.stdin.fileno()
    viejo = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        t = sys.stdin.read(1)
        if t == "\x1b":
            resto = sys.stdin.read(2)
            return {"[A": "arriba", "[B": "abajo"}.get(resto, "")
        if t in ("\r", "\n"):
            return "enter"
        return t.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, viejo)


def pintar(seleccion: int) -> None:
    limpiar()
    print(f"{Color.titulo}" + "=" * ANCHO + f"{Color.fin}")
    print(f"{Color.titulo}  KYNIKOS · centro de comando{Color.fin}")
    print(f"{Color.titulo}" + "=" * ANCHO + f"{Color.fin}")
    puerto = puerto_nodo()
    vivo = nodo_vivo()
    marca = f"{Color.ok}nodo arriba{Color.fin}" if vivo else f"{Color.mal}nodo abajo{Color.fin}"
    extra = f"puerto {puerto}" if vivo else f"puerto {puerto} libre"
    print(f"  {marca}   {Color.gris}{extra} · {modelo_activo()}{Color.fin}")
    print()
    for i, (texto, _) in enumerate(OPCIONES):
        if i == seleccion:
            print(f"  {Color.sel} > {i + 1}. {texto:<24}{Color.fin}")
        else:
            print(f"    {i + 1}. {texto}")
    print()
    print(f"{Color.gris}  flechas para moverte, Enter para elegir, q para salir{Color.fin}")


def principal() -> int:
    _habilitar_ansi()
    if not (RAIZ / "cli" / "kynikos.py").exists():
        print(f"No encuentro cli/kynikos.py en {RAIZ}")
        print("Ejecuta este archivo desde el repositorio KynicOS:  python nodo\\centro.py")
        return 1
    seleccion = 0
    try:
        while True:
            pintar(seleccion)
            tecla = _leer_tecla()
            if tecla == "q":
                limpiar()
                return 0
            if tecla == "arriba":
                seleccion = (seleccion - 1) % len(OPCIONES)
            elif tecla == "abajo":
                seleccion = (seleccion + 1) % len(OPCIONES)
            elif tecla == "enter":
                limpiar()
                texto, funcion = OPCIONES[seleccion]
                if funcion is None:
                    return 0
                print(f"{Color.titulo}>> {texto}{Color.fin}")
                try:
                    funcion()
                except Exception as e:
                    mal(f"la acción falló: {e}")
                print()
                input(f"{Color.gris}  Enter para volver{Color.fin}")
    except KeyboardInterrupt:
        limpiar()
        return 0


if __name__ == "__main__":
    sys.exit(principal())
