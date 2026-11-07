#!/usr/bin/env python3
"""KYNIKOS CLI — instalación configurable del nodo en cualquier computadora.

Un solo ejecutable, sin dependencias externas (solo biblioteca estándar), que
detecta el hardware, recomienda el modelo que cabe de verdad, prepara el entorno
y enlaza el bot con Telegram.

Uso:
    python3 cli/kynikos.py doctor          # qué tiene esta máquina
    python3 cli/kynikos.py plan            # qué modelo le corresponde
    python3 cli/kynikos.py init            # crea .env guiado
    python3 cli/kynikos.py telegram        # estado del bot y del webhook
    python3 cli/kynikos.py install         # instala Ollama y dependencias
    python3 cli/kynikos.py run             # arranca el nodo
    python3 cli/kynikos.py service         # unidad systemd o tarea de Windows
    python3 cli/kynikos.py status          # salud del nodo local
    python3 cli/kynikos.py models          # modelos instalados en Ollama
    python3 cli/kynikos.py config          # ver o cambiar .env

Todos los comandos aceptan --json para uso programático y --ruta para trabajar
sobre otra copia del proyecto. Nunca imprime tokens: enmascara cualquier valor
sensible que muestre.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENV = RAIZ / ".env"
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# Modelos candidatos: (etiqueta, parámetros en miles de millones, nota)
# (etiqueta, parámetros, nota, factor de calidad en español)
# El factor desempata: el bot conversa en español, y qwen2.5 rinde mejor en es
# que llama para el mismo tamaño. Sin este sesgo se elegiría un modelo peor en idioma.
CANDIDATOS = [
    ("qwen2.5:3b", 3.0, "respuestas rápidas, razonamiento limitado", 1.00),
    ("llama3.2:3b", 3.2, "ligero, bueno para tareas cortas", 0.85),
    ("qwen2.5:7b", 7.0, "punto dulce en 8-16 GB", 1.00),
    ("llama3.1:8b", 8.0, "alternativa a 7B, algo más lento", 0.85),
    ("qwen2.5:14b", 14.0, "mejor razonamiento, requiere 12 GB libres", 1.00),
    ("qwen2.5:32b", 32.0, "solo con 24 GB+ de GPU dedicada", 1.00),
    ("llama3.3:70b", 70.0, "requiere 48 GB+; experimental", 0.85),
]

# Ancho de banda aproximado en GB/s para estimar tokens por segundo.
BANDA_CPU_DDR4 = 45.0      # dual channel DDR4-3200
BANDA_CPU_DDR5 = 75.0
BANDA_GPU = {               # por clase de VRAM dedicada
    4: 110.0, 6: 190.0, 8: 290.0, 12: 360.0, 16: 450.0, 24: 900.0,
}

RESERVA_SO = {"Windows": 3.5, "Linux": 1.0, "Darwin": 4.0}


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------
def enmascarar(valor: str) -> str:
    if not valor:
        return "(vacío)"
    if len(valor) <= 8:
        return "*" * len(valor)
    return valor[:4] + "…" + valor[-2:] + f" ({len(valor)} caracteres)"


def correr(comando: list[str], timeout: int = 15) -> str:
    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=timeout)
        return (resultado.stdout or "").strip()
    except Exception:
        return ""


def leer_json_url(url: str, timeout: int = 8) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read().decode())
        except Exception:
            return {"error": f"HTTP {error.code}"}
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"}


def leer_env() -> dict[str, str]:
    datos: dict[str, str] = {}
    if ENV.exists():
        for linea in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            datos[clave.strip()] = valor.strip()
    return datos


def escribir_env(datos: dict[str, str]) -> None:
    lineas = [
        "# Generado por kynikos init. No lo subas al repositorio.",
        f"# {platform.node()} · {platform.system()} {platform.release()}",
    ]
    for clave, valor in datos.items():
        lineas.append(f"{clave}={valor}")
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    try:
        ENV.chmod(0o600)
    except Exception:
        pass


# --------------------------------------------------------------------------
# detección de hardware
# --------------------------------------------------------------------------
def memoria_total_gb() -> float:
    sistema = platform.system()
    try:
        if sistema == "Linux":
            for linea in Path("/proc/meminfo").read_text().splitlines():
                if linea.startswith("MemTotal:"):
                    return round(int(linea.split()[1]) / 1024 / 1024, 1)
        elif sistema == "Darwin":
            salida = correr(["sysctl", "-n", "hw.memsize"])
            if salida.isdigit():
                return round(int(salida) / 1024**3, 1)
        elif sistema == "Windows":
            import ctypes

            class MemStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            estado = MemStatus()
            estado.dwLength = ctypes.sizeof(MemStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado))
            return round(estado.ullTotalPhys / 1024**3, 1)
    except Exception:
        pass
    return 0.0


def memoria_disponible_gb() -> float:
    sistema = platform.system()
    try:
        if sistema == "Linux":
            for linea in Path("/proc/meminfo").read_text().splitlines():
                if linea.startswith("MemAvailable:"):
                    return round(int(linea.split()[1]) / 1024 / 1024, 1)
        elif sistema == "Darwin":
            salida = correr(["vm_stat"])
            paginas = 0
            for linea in salida.splitlines():
                if "Pages free" in linea or "Pages inactive" in linea:
                    numero = "".join(c for c in linea.split(":")[-1] if c.isdigit())
                    paginas += int(numero or 0)
            return round(paginas * 4096 / 1024**3, 1)
    except Exception:
        pass
    return memoria_total_gb()


def cpu_info() -> dict:
    sistema = platform.system()
    modelo = platform.processor() or platform.machine()
    nucleos = os.cpu_count() or 0
    if sistema == "Linux":
        try:
            for linea in Path("/proc/cpuinfo").read_text().splitlines():
                if linea.startswith("model name"):
                    modelo = linea.split(":", 1)[1].strip()
                    break
        except Exception:
            pass
    elif sistema == "Darwin":
        modelo = correr(["sysctl", "-n", "machdep.cpu.brand_string"]) or modelo
    elif sistema == "Windows":
        modelo = correr(["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_Processor).Name"]) or modelo
    return {"modelo": modelo.strip(), "nucleos": nucleos}


def gpu_info() -> dict:
    """Detecta GPU dedicada y su VRAM. Devuelve VRAM 0 si es integrada."""
    sistema = platform.system()
    nombre, vram_mb = "", 0

    salida = correr(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if salida:
        partes = salida.splitlines()[0].split(",")
        nombre = partes[0].strip()
        try:
            vram_mb = int(partes[1].strip())
        except Exception:
            vram_mb = 0

    if not nombre and sistema == "Windows":
        salida = correr(["powershell", "-NoProfile", "-Command",
                         "Get-CimInstance Win32_VideoController | "
                         "Select-Object Name,AdapterRAM | ConvertTo-Json -Compress"])
        if salida:
            try:
                datos = json.loads(salida)
                datos = datos if isinstance(datos, list) else [datos]
                mejor = max(datos, key=lambda d: d.get("AdapterRAM") or 0)
                nombre = (mejor.get("Name") or "").strip()
                vram_mb = int((mejor.get("AdapterRAM") or 0) / 1024**2)
            except Exception:
                pass

    if not nombre and sistema == "Linux":
        salida = correr(["bash", "-c", "lspci | grep -Ei 'vga|3d|display' | head -1"])
        nombre = salida.split(":")[-1].strip() if salida else ""

    integrada = any(x in nombre.lower() for x in
                    ("radeon", "vega", "intel", "uhd", "iris", "integrated"))
    # AdapterRAM en Windows miente con iGPU (reporta 496 MB); se trata como integrada
    if integrada or vram_mb < 1024:
        return {"nombre": nombre or "desconocida", "vram_gb": 0.0, "dedicada": False}
    return {"nombre": nombre, "vram_gb": round(vram_mb / 1024, 1), "dedicada": True}


def disco_libre_gb() -> float:
    try:
        return round(shutil.disk_usage(str(RAIZ)).free / 1024**3, 1)
    except Exception:
        return 0.0


def recolectar() -> dict:
    sistema = platform.system()
    cpu = cpu_info()
    gpu = gpu_info()
    total = memoria_total_gb()
    disponible = memoria_disponible_gb()
    reserva = RESERVA_SO.get(sistema, 2.0)
    util_memoria = max(total - reserva, 0)
    ancho = BANDA_CPU_DDR5 if "ddr5" in cpu["modelo"].lower() else BANDA_CPU_DDR4
    if gpu["dedicada"]:
        clase = min(BANDA_GPU, key=lambda v: abs(v - gpu["vram_gb"]))
        ancho = max(ancho, BANDA_GPU[clase])
    return {
        "so": f"{sistema} {platform.release()}",
        "equipo": platform.node(),
        "cpu": cpu,
        "ram_total_gb": total,
        "ram_disponible_gb": disponible,
        "ram_utilizable_gb": round(util_memoria, 1),
        "gpu": gpu,
        "disco_libre_gb": disco_libre_gb(),
        "ancho_banda_gbs": ancho,
        "ollama_instalado": bool(shutil.which("ollama")),
        "python": platform.python_version(),
    }


# --------------------------------------------------------------------------
# planificador
# --------------------------------------------------------------------------
def planificar(datos: dict) -> dict:
    capacidad = datos["ram_utilizable_gb"]
    if datos["gpu"]["dedicada"]:
        capacidad = max(capacidad, datos["gpu"]["vram_gb"])

    opciones = []
    for etiqueta, params, nota, factor_es in CANDIDATOS:
        peso = params * 0.55 + 1.2          # Q4_K_M + caché de contexto 4k
        cabe = peso <= capacidad - 1.0
        tps = round((datos["ancho_banda_gbs"] / peso) * 0.6, 1)
        opciones.append({
            "modelo": etiqueta, "parametros_b": params, "peso_gb": round(peso, 1),
            "cabe": cabe, "tokens_por_segundo": tps,
            "tokens_en_5_min": int(tps * 300), "nota": nota,
            "puntaje_es": round(params * factor_es, 2),
        })

    aptos = [o for o in opciones if o["cabe"]]
    # Criterio: el mayor modelo que mantenga al menos 4 tok/s (chat cómodo).
    # Por debajo de 4 tok/s la conversación se siente rota aunque quepa en RAM.
    usables = [o for o in aptos if o["tokens_por_segundo"] >= 4.0]
    elegido = max(usables, key=lambda o: o["puntaje_es"]) if usables else (aptos[0] if aptos else None)
    maximo = max(aptos, key=lambda o: o["puntaje_es"]) if aptos else None

    if elegido and elegido["tokens_por_segundo"] >= 6:
        max_tokens = 1024
    elif elegido:
        max_tokens = 768
    else:
        max_tokens = 512

    return {
        "capacidad_gb": round(capacidad, 1),
        "elegido": elegido,
        "maximo_que_cabe": maximo,
        "opciones": opciones,
        "config": {
            "OLLAMA_MODEL": elegido["modelo"] if elegido else "qwen2.5:3b",
            "OLLAMA_NUM_CTX": 4096,
            "MAX_TOKENS_SALIDA": max_tokens,
            "TIMEOUT_LLM": 300,
        },
        "veredicto": (
            f"{elegido['modelo']} ({elegido['peso_gb']} GB, ~{elegido['tokens_por_segundo']} tok/s)"
            if elegido else "ningún modelo cabe con margen; libera RAM o usa un modelo en la nube"
        ),
        "techo": (
            f"{maximo['modelo']} ({maximo['peso_gb']} GB, ~{maximo['tokens_por_segundo']} tok/s)"
            if maximo else "sin techo calculable"
        ),
    }


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------
def cmd_doctor(args) -> int:
    datos = recolectar()
    plan = planificar(datos)
    if args.json:
        print(json.dumps({**datos, "plan": plan}, indent=2, ensure_ascii=False))
        return 0

    gpu = datos["gpu"]
    print(f"Equipo      {datos['equipo']} · {datos['so']} · Python {datos['python']}")
    print(f"CPU         {datos['cpu']['modelo']} ({datos['cpu']['nucleos']} hilos)")
    print(f"RAM         {datos['ram_total_gb']} GB total · {datos['ram_disponible_gb']} GB libre · "
          f"{datos['ram_utilizable_gb']} GB utilizables tras el SO")
    tipo = f"{gpu['vram_gb']} GB dedicados" if gpu["dedicada"] else "integrada, sin VRAM propia"
    print(f"GPU         {gpu['nombre']} ({tipo})")
    print(f"Disco       {datos['disco_libre_gb']} GB libres")
    print(f"Ollama      {'instalado' if datos['ollama_instalado'] else 'NO instalado'}")
    print()
    print(f"Modelo recomendado: {plan['veredicto']}")
    print("Modelos que caben:")
    for o in plan["opciones"]:
        if o["cabe"]:
            marca = "◀ elegido" if plan["elegido"] and o["modelo"] == plan["elegido"]["modelo"] else ""
            print(f"  {o['modelo']:16} {o['peso_gb']:5.1f} GB  ~{o['tokens_por_segundo']:4.1f} tok/s  {marca}")
    fuera = [o["modelo"] for o in plan["opciones"] if not o["cabe"]]
    if fuera:
        print(f"No caben: {', '.join(fuera)}")
    return 0


def cmd_plan(args) -> int:
    plan = planificar(recolectar())
    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    print(f"Capacidad útil: {plan['capacidad_gb']} GB")
    print(f"Elegido: {plan['veredicto']}")
    print("\n.env sugerido:")
    for clave, valor in plan["config"].items():
        print(f"  {clave}={valor}")
    return 0


def cmd_init(args) -> int:
    datos = recolectar()
    plan = planificar(datos)
    previos = leer_env()

    token = args.token or previos.get("TELEGRAM_TOKEN", "")
    if not token:
        print("Token del bot (se guarda en .env, no se muestra): ", end="", flush=True)
        try:
            import getpass
            token = getpass.getpass("")
        except Exception:
            token = sys.stdin.readline().strip()

    usuario = args.usuario or previos.get("TELEGRAM_USER_ID", "8247886073")
    modelo = args.modelo or plan["config"]["OLLAMA_MODEL"]

    valores = {
        "TELEGRAM_TOKEN": token,
        "TELEGRAM_USER_ID": usuario,
        "PERSONA": "kynikos",
        "OLLAMA_URL": OLLAMA,
        "OLLAMA_MODEL": modelo,
        "OLLAMA_NUM_CTX": str(plan["config"]["OLLAMA_NUM_CTX"]),
        "MAX_TOKENS_SALIDA": str(plan["config"]["MAX_TOKENS_SALIDA"]),
        "TIMEOUT_LLM": str(plan["config"]["TIMEOUT_LLM"]),
    }
    escribir_env(valores)
    print(f"Escrito {ENV} (permisos 600)")
    print(f"  token: {enmascarar(token)}")
    print(f"  modelo: {modelo} · contexto {valores['OLLAMA_NUM_CTX']} · salida {valores['MAX_TOKENS_SALIDA']}")
    print("\nSiguiente paso: kynikos install && kynikos telegram")
    return 0


def cmd_telegram(args) -> int:
    valores = leer_env()
    token = (args.token
             or os.environ.get("TELEGRAM_TOKEN")
             or os.environ.get("TELEGRAM_BOT_TOKEN")      # alias de la plataforma
             or valores.get("TELEGRAM_TOKEN", ""))
    if not token:
        print("Sin token. Usa `kynikos init` o la variable TELEGRAM_TOKEN.")
        return 2
    base = f"https://api.telegram.org/bot{token}"

    identidad = leer_json_url(base + "/getMe")
    if not identidad.get("ok"):
        print(f"Token inválido o sin red: {identidad.get('error') or identidad.get('description')}")
        return 2
    bot = identidad["result"]

    info = leer_json_url(base + "/getWebhookInfo")
    webhook = (info.get("result") or {})
    url = webhook.get("url") or ""

    if args.liberar:
        if not url:
            print("No hay webhook que liberar.")
        else:
            resultado = leer_json_url(base + "/deleteWebhook?drop_pending_updates=false")
            print("Webhook eliminado." if resultado.get("ok") else f"Fallo: {resultado}")

    if args.configurar:
        hechos = configurar_bot(base)
        print("Perfil del bot: " + ", ".join(f"{k}={'ok' if v else 'falló'}" for k, v in hechos.items()))

    if args.webhook:
        url_destino = f"{args.webhook.rstrip('/')}/api/telegram"
        resultado = leer_json_url(base + "/setWebhook?url=" + urllib.parse.quote(url_destino, safe=""))
        print("Webhook registrado en " + url_destino if resultado.get("ok") else f"Fallo: {resultado}")

    if args.json:
        print(json.dumps({"bot": bot, "webhook": webhook}, indent=2, ensure_ascii=False))
        return 0

    print(f"Bot        @{bot.get('username')} · id {bot.get('id')} · nombre {bot.get('first_name')}")
    if url:
        print(f"Webhook    {url}")
        if "base44.com" in url:
            print("           ⚠ apunta a la plataforma Base44: mientras exista, el nodo NO puede usar polling")
            print("           usa `kynikos telegram --liberar` si ese bot no lo ocupa otro agente")
    else:
        print("Webhook    ninguno (modo polling disponible)")
    print(f"Pendientes {webhook.get('pending_update_count', 0)}")
    return 0


def configurar_bot(base: str, nombre: str = "KYNIKOS") -> dict:
    """Deja el bot presentable: descripción, descripción corta y comandos.

    Idempotente: se puede repetir sin efectos secundarios. No envía mensajes.
    """
    descripcion = (f"{nombre} · nodo primario de Julián Juárez. Seguridad, infraestructura y "
                   "automatización. Corre en hardware propio con modelo local: sin techo de tokens.")
    comandos = [
        {"command": "estado", "description": "salud del nodo y modelo activo"},
        {"command": "modelo", "description": "qué modelo está corriendo"},
        {"command": "reiniciar", "description": "limpia el contexto de la conversación"},
        {"command": "ayuda", "description": "qué sabe hacer y qué no"},
    ]
    resultados = {}
    resultados["descripcion"] = leer_json_url(
        base + "/setMyDescription?description=" + urllib.parse.quote(descripcion, safe="")).get("ok", False)
    resultados["descripcion_corta"] = leer_json_url(
        base + "/setMyShortDescription?short_description="
        + urllib.parse.quote("Perro guardián técnico. Nodo propio, modelo local.", safe="")).get("ok", False)
    cuerpo = json.dumps({"commands": comandos}).encode()
    try:
        peticion = urllib.request.Request(base + "/setMyCommands", data=cuerpo,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(peticion, timeout=10) as r:
            resultados["comandos"] = json.loads(r.read().decode()).get("ok", False)
    except Exception:
        resultados["comandos"] = False
    return resultados


def cmd_install(args) -> int:
    datos = recolectar()
    sistema = platform.system()
    plan = planificar(datos)
    modelo = args.modelo or plan["config"]["OLLAMA_MODEL"]

    if sistema == "Windows":
        print("En Windows ejecuta en PowerShell:")
        print("  winget install --id Ollama.Ollama -e")
        print(f"  ollama pull {modelo}")
        print("  python -m venv .venv; .venv\\Scripts\\pip install -r requirements-bot.txt")
        return 0

    if not datos["ollama_instalado"]:
        print("Ollama no está instalado. Comando oficial:")
        print("  curl -fsSL https://ollama.com/install.sh | sh")
        if not args.si:
            print("(añade --si para que este CLI lo ejecute)")
            return 1
        if subprocess.run(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]).returncode != 0:
            print("La instalación de Ollama falló")
            return 1

    venv = RAIZ / ".venv"
    if not venv.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=False)
    pip = venv / "bin" / "pip"
    if pip.exists():
        subprocess.run([str(pip), "install", "-q", "--upgrade", "pip"], check=False)
        subprocess.run([str(pip), "install", "-q", "-r", str(RAIZ / "requirements-bot.txt")], check=False)

    print(f"Descargando modelo {modelo} (una sola vez)")
    subprocess.run(["ollama", "pull", modelo], check=False)
    print("\nListo. Siguiente: kynikos telegram && kynikos run")
    return 0


def cmd_run(args) -> int:
    valores = leer_env()
    entorno = {**os.environ, **valores}
    print(f"Arrancando nodo con {valores.get('OLLAMA_MODEL', 'modelo por defecto')}…")

    # execve SUSTITUYE este proceso; subprocess creaba un hijo. Con el hijo
    # habia dos PIDs: el CLI y el servidor. El lanzador informaba el del CLI
    # como 'el que atiende' (mentira: atendia el hijo) y al detener uno quedaba
    # el otro vivo peleando el puerto y el long-poll de Telegram.
    sys.stdout.flush()
    try:
        os.chdir(str(RAIZ))
        os.execve(sys.executable, [sys.executable, "-m", "app.main"], entorno)
    except OSError as e:
        print(f"no pude sustituir el proceso ({e}); arranco como hijo")
        return subprocess.run([sys.executable, "-m", "app.main"], cwd=str(RAIZ), env=entorno).returncode


def cmd_status(args) -> int:
    salud = leer_json_url(OLLAMA.replace("/api", "") + "/api/tags", timeout=4)
    modelos = [m.get("name") for m in (salud.get("models") or [])] if "error" not in salud else []
    valores = leer_env()
    estado = {
        "ollama_respondiendo": "error" not in salud,
        "modelos_instalados": modelos,
        "token_configurado": bool(valores.get("TELEGRAM_TOKEN")),
        "persona": valores.get("PERSONA", "kynikos"),
        "modelo_configurado": valores.get("OLLAMA_MODEL", "(sin definir)"),
        "env_existe": ENV.exists(),
    }
    if args.json:
        print(json.dumps(estado, indent=2, ensure_ascii=False))
        return 0
    print(f"Ollama      {'responde' if estado['ollama_respondiendo'] else 'no responde'}")
    print(f"Modelos     {', '.join(modelos) if modelos else '(ninguno instalado)'}")
    print(f"Config      {estado['modelo_configurado']} · persona {estado['persona']}")
    print(f"Token       {'configurado' if estado['token_configurado'] else 'FALTA'}")
    print(f".env        {'presente' if estado['env_existe'] else 'ausente'}")
    return 0


def cmd_models(args) -> int:
    salud = leer_json_url(OLLAMA.replace("/api", "") + "/api/tags", timeout=4)
    if "error" in salud:
        print(f"Ollama no responde en {OLLAMA}: {salud['error']}")
        return 1
    modelos = salud.get("models") or []
    if not modelos:
        print("Sin modelos instalados.")
    for m in modelos:
        gb = round((m.get("size") or 0) / 1024**3, 1)
        print(f"  {m.get('name'):28} {gb:5.1f} GB")
    plan = planificar(recolectar())
    print(f"\nEste equipo pide: {plan['veredicto']}")
    return 0


def cmd_config(args) -> int:
    valores = leer_env()
    if not args.cambiar:
        for clave, valor in valores.items():
            mostrado = enmascarar(valor) if "TOKEN" in clave or "KEY" in clave else valor
            print(f"{clave}={mostrado}")
        return 0
    for par in args.cambiar:
        if "=" not in par:
            print(f"Ignorado (formato clave=valor): {par}")
            continue
        clave, _, valor = par.partition("=")
        valores[clave.strip()] = valor.strip()
        print(f"{clave.strip()} actualizado")
    escribir_env(valores)
    return 0


def cmd_doble_paso(args) -> int:
    """Opera el flujo de doble paso desde la consola del nodo."""
    sys.path.insert(0, str(RAIZ))
    try:
        from app.security import doble_paso as dp
    except Exception as error:  # noqa: BLE001
        print(f"No se pudo cargar el módulo de doble paso: {type(error).__name__}")
        return 2

    accion = (args.extra[0] if args.extra else "estado").lower()

    if accion == "estado":
        estado = dp.estado_publico()
        if args.json:
            print(json.dumps(estado, indent=2, ensure_ascii=False))
            return 0
        print(f"Primer paso configurado  {'sí' if estado['configurado'] else 'NO (define KYNIKOS_PALABRA_1)'}")
        print(f"Solicitudes pendientes   {estado['pendientes']}")
        print(f"Bloqueado                {'sí' if estado['bloqueado'] else 'no'}")
        print(f"Ventana de autorización  {estado['ttl_solicitud_s']} s")
        print(f"Vida de la palabra       {estado['vida_palabra_s']} s")
        return 0

    if accion == "solicitar":
        try:
            solicitud, nueva = dp.solicitar(args.chat or 0)
        except dp.ErrorDoblePaso as error:
            print(f"No se pudo solicitar: {error}")
            return 1
        print(f"Solicitud {'creada' if nueva else 'reutilizada'}: {solicitud.id}")
        print("Ahora falta la autorización por Telegram (botón) antes de emitir palabra.")
        return 0

    if accion == "verificar":
        if len(args.extra) < 2:
            print("Falta la palabra. Uso: kynikos doble-paso verificar KALPIXK-XXXX-XXXX")
            return 2
        ok = dp.verificar(args.extra[1])
        print("Palabra válida y consumida." if ok else "Palabra inválida, vencida o ya usada.")
        return 0 if ok else 1

    print("Acciones: estado | solicitar | verificar <palabra>")
    return 2


def cmd_service(args) -> int:
    sistema = platform.system()
    if sistema == "Windows":
        print("Tarea de Windows (ejecutar en PowerShell como administrador):")
        print(f'  schtasks /create /tn KYNIKOS /tr "{sys.executable} {RAIZ / "app" / "main.py"}" '
              f'/sc onstart /rl highest')
        return 0
    unidad = f"""[Unit]
Description=KYNIKOS nodo primario
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=simple
User={os.environ.get('USER', 'root')}
WorkingDirectory={RAIZ}
EnvironmentFile={ENV}
ExecStart={RAIZ / '.venv' / 'bin' / 'python'} -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    destino = RAIZ / "nodo" / "kynikos.service"
    destino.write_text(unidad)
    print(f"Unidad generada en {destino}")
    print("Instalar con:")
    print(f"  sudo cp {destino} /etc/systemd/system/ && sudo systemctl enable --now kynikos")
    return 0


COMANDOS = {
    "doctor": cmd_doctor,
    "plan": cmd_plan,
    "init": cmd_init,
    "telegram": cmd_telegram,
    "install": cmd_install,
    "run": cmd_run,
    "status": cmd_status,
    "models": cmd_models,
    "config": cmd_config,
    "service": cmd_service,
    "doble-paso": cmd_doble_paso,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kynikos",
        description="Instalación configurable del nodo KYNIKOS en cualquier computadora.",
    )
    parser.add_argument("comando", choices=sorted(COMANDOS), help="qué hacer")
    parser.add_argument("--json", action="store_true", help="salida legible por máquina")
    parser.add_argument("--token", help="token del bot (mejor por variable de entorno)")
    parser.add_argument("--usuario", help="id de Telegram autorizado")
    parser.add_argument("--modelo", help="modelo de Ollama a usar")
    parser.add_argument("--webhook", help="URL pública para registrar el webhook")
    parser.add_argument("--liberar", action="store_true", help="eliminar webhook existente")
    parser.add_argument("--si", action="store_true", help="confirmar acciones del instalador")
    parser.add_argument("--configurar", action="store_true",
                        help="deja descripción y comandos del bot listos")
    parser.add_argument("--cambiar", nargs="*", help="clave=valor para config")
    parser.add_argument("--chat", type=int, help="chat de Telegram para la solicitud")
    parser.add_argument("extra", nargs="*", help="acción y argumentos del comando")
    args = parser.parse_args()
    return COMANDOS[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
