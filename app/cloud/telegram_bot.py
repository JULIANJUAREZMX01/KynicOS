"""Telegram bot integration for KynicOS with Agent Loop."""

import html
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.config import Settings
from app.utils import get_logger
from app.core.context import AgentContext

logger = get_logger(__name__)
_app: Optional[Application] = None
# El loop y el session manager se INYECTAN al arrancar. Antes se importaban
# desde app.main dentro del handler, pero con `python -m app.main` ese codigo
# vive como __main__: el import creaba una segunda copia del modulo en la que
# _agent_loop seguia en None, y todo mensaje libre respondia
# "Agent loop no iniciado". Pasarlos por parametro elimina el import cruzado.
_loop = None
_sessions = None
_arranque: Optional[float] = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start using the configured KynicOS persona."""
    user = update.effective_user
    message = update.message
    if not message:
        return

    try:
        import os
        from app.config import Settings
        from app.concierge.persona import get_persona

        # Una sola fuente de verdad para la persona. Antes aqui se leia
        # os.getenv("PERSONA", "leo") mientras /api/status leia
        # os.getenv("PERSONA", Settings().persona): con el .env sin PERSONA,
        # /start saludaba como Leo (concierge de hotel) y el status decia
        # kynicos. Dos respaldos distintos para la misma variable.
        persona = get_persona(os.getenv("PERSONA", Settings().persona))
        greeting = persona.greeting
    except Exception:
        greeting = "🛡️ KYNIKOS en línea. ¿Qué atacamos hoy, jefe?"

    await message.reply_text(f"Hola {user.first_name}! 👋\n\n{greeting}")
    logger.info(f"User {user.id} started KynicOS bot")


def _texto_log(ruta, lineas=12):
    """Ultimas lineas del registro, sin reventar si no existe."""
    from pathlib import Path
    f = Path(ruta)
    if not f.exists():
        return "(todavia no hay registro)"
    try:
        with f.open("r", encoding="utf-8", errors="replace") as fh:
            contenido = fh.readlines()[-lineas:]
        return "".join(contenido).strip() or "(registro vacio)"
    except Exception as e:
        return f"(no se pudo leer: {e})"


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista de comandos."""
    texto = (
        "<b>KYNIKOS · comandos</b>\n\n"
        "/estado  — salud del nodo: modelo, memoria, proceso\n"
        "/modelo  — modelo activo y ventana de contexto\n"
        "/logs  — ultimas lineas del registro\n"
        "/id  — tu ID de Telegram\n"
        "/actualizar — trae el repo y reinicia el nodo desde aqui\n"
        "/ecosistema — repos presentes en disco\n"
        "/ecosistema_buscar texto — busca en repos permitidos\n"
        "/ecosistema_leer repo ruta — lee un archivo de texto\n"
        "/reiniciar  — revisa si el polling esta vivo\n"
        "/ayuda  — esta lista\n\n"
        "Cualquier otro mensaje lo responde el agente."
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def actualizar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trae el repo y reinicia el nodo, todo desde Telegram.

    Matar el updater desde dentro del propio handler deja al bot mudo (paso el
    6-nov). La salida segura: se lanza un proceso EXTERNO (kynikos.ps1 reiniciar)
    desacoplado, con una espera para que este mensaje salga antes de que el
    proceso viejo muera. El script valida que el nodo vuelva antes de dar OK, y
    al arrancar el nodo nuevo avisa por Telegram: si no llega ese aviso, algo
    fallo y hay que mirar la PC.
    """
    import asyncio
    import subprocess
    import sys
    from pathlib import Path

    chat = update.effective_chat
    repo = Path(__file__).resolve().parents[2]
    await chat.send_message("🔄 Trayendo cambios del repositorio...")

    def git(*args: str, limite: int = 90):
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=limite
        )

    try:
        antes = git("rev-parse", "--short", "HEAD").stdout.strip()
        git("fetch", "--quiet", "origin", "main")
        merge = git("merge", "--ff-only", "origin/main")
        despues = git("rev-parse", "--short", "HEAD").stdout.strip()
    except subprocess.TimeoutExpired:
        await chat.send_message("⛔ El repositorio no respondio a tiempo. No reinicio: el nodo sigue como estaba.")
        return
    except Exception as e:
        await chat.send_message(f"⛔ No pude actualizar: {str(e)[:120]}\nEl nodo sigue como estaba.")
        return

    if merge.returncode != 0:
        detalle = (merge.stderr or merge.stdout).strip()[:300]
        await chat.send_message(
            "⛔ <b>No actualicé</b>: el repo no avanzó en linea recta (hay cambios locales "
            "o conflicto).\nNo reinicio para no dejarte sin nodo.\n\n"
            f"<pre>{detalle}</pre>"
        )
        return

    if antes == despues:
        resumen = f"Sin cambios nuevos (sigo en <code>{antes}</code>)."
    else:
        resumen = f"Actualizado <code>{antes}</code> → <code>{despues}</code>."

    await chat.send_message(f"✅ {resumen}\n\n🔁 Reiniciando el nodo... vuelvo en ~60s.")

    # Proceso externo: sobrevive a la muerte de este. La espera da tiempo a que
    # el mensaje anterior salga por Telegram antes de que maten este proceso.
    guion = repo / "nodo" / "kynikos.ps1"
    try:
        if sys.platform == "win32":
            orden = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"Start-Sleep -Seconds 5; & '{guion}' reiniciar",
            ]
            banderas = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen(orden, cwd=str(repo), close_fds=True,
                             creationflags=banderas, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(
                ["bash", "-c", f"sleep 5; '{guion}' reiniciar"],
                cwd=str(repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
            )
        logger.info("Reinicio programado desde Telegram; el proceso externo reemplaza al nodo")
    except Exception as e:
        logger.error(f"No pude programar el reinicio: {e}", exc_info=True)
        await chat.send_message(
            f"⚠️ Actualicé a <code>{despues}</code> pero no pude relanzar el nodo: {str(e)[:120]}\n"
            "El bot sigue vivo con el codigo viejo. Reintenta /actualizar."
        )


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Salud real del nodo, sin inventar metricas."""
    import os
    import time
    from app.config import Settings
    from app.cloud import telegram_bot as tb

    ajustes = Settings()
    lineas = ["<b>KYNIKOS · estado</b>", ""]
    lineas.append(f"Modelo: <code>{ajustes.ollama_model}</code>")
    lineas.append(f"Contexto: {ajustes.ollama_num_ctx} tokens")
    lineas.append(f"Salida max: {ajustes.max_tokens_salida}")
    lineas.append(f"PID: {os.getpid()}")

    arranque = getattr(tb, "_arranque", None)
    if arranque:
        minutos = int((time.time() - arranque) / 60)
        lineas.append(f"Encendido hace: {minutos} min")

    try:
        import psutil
        proc = psutil.Process(os.getpid())
        lineas.append(f"RAM del nodo: {proc.memory_info().rss / 1024**2:.0f} MB")
    except Exception:
        pass

    polling = "activo" if tb._app and tb._app.updater and tb._app.updater.running else "detenido"
    lineas.append(f"Polling: {polling}")

    await update.message.reply_text("\n".join(lineas), parse_mode="HTML")


async def modelo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Modelo y proveedor configurados."""
    from app.config import Settings
    a = Settings()
    texto = (
        "<b>Modelo</b>\n"
        f"Ollama: <code>{a.ollama_model}</code>\n"
        f"URL: <code>{a.ollama_url}</code>\n"
        f"Contexto: {a.ollama_num_ctx}\n"
        f"Timeout: {a.timeout_llm:g} s"
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ultimas lineas del registro del nodo."""
    import os
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[2]
    texto = _texto_log(raiz / "kynikos.log")
    if len(texto) > 3500:
        texto = texto[-3500:]
    await update.message.reply_text(f"<pre>{texto}</pre>", parse_mode="HTML")


async def mi_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ID de Telegram del remitente."""
    u = update.effective_user
    await update.message.reply_text(
        f"Tu ID: <code>{u.id}</code>\nChat: <code>{update.effective_chat.id}</code>",
        parse_mode="HTML",
    )


async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Informa del estado del polling SIN matar el updater.

    Antes hacia stop + sleep + start DENTRO del propio handler. stop_telegram_bot()
    detiene el updater, y detenerlo cancela la tarea que esta ejecutando este
    mismo codigo: start_telegram_bot() nunca llegaba a correr y el bot quedaba
    mudo hasta reiniciar el proceso. Paso el 6-nov: /reiniciar respondio
    "Reiniciando el bot..." y despues no contesto nada, ni /estado.

    Desde aqui no se puede reiniciar el updater de forma segura. Si esta vivo,
    se confirma; si esta caido, se levanta (eso si es seguro, porque no hay
    updater que cancelar).
    """
    from app.cloud import telegram_bot as tb

    vivo = bool(tb._app and tb._app.updater and tb._app.updater.running)
    if vivo:
        await update.effective_chat.send_message(
            "Polling activo y respondiendo.\n\n"
            "Polling vivo. Para traer cambios y reiniciar de verdad usa "
            "/actualizar: lanza el reinicio desde un proceso externo, asi no se "
            "cancela a si mismo."
        )
        return

    try:
        from app.config import Settings
        await start_telegram_bot(Settings())
        await update.effective_chat.send_message("El polling estaba caido; lo levante de nuevo.")
        logger.info("Polling levantado desde Telegram (estaba caido)")
    except Exception as e:
        logger.error(f"No pude levantar el polling: {e}")
        await update.effective_chat.send_message(f"No pude levantarlo: {e}")


async def instalar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Diagnóstico del nodo a partir de sus registros.

    Determinista: no pasa por el modelo, así que no puede inventar la causa.
    Nació de la noche del 6-nov, cuando todo el diagnóstico lo hizo una persona
    leyendo pantallas mientras el bot solo decía que no arrancaba.
    """
    from app.core.diagnostico import texto_para_usuario
    try:
        texto = texto_para_usuario()
    except Exception as e:
        logger.error(f"Error en /instalar: {e}")
        texto = "No pude leer los registros del nodo."
    await update.message.reply_text(texto, parse_mode="HTML")


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Version local frente a la ultima publicada, sin tocar nada."""
    import subprocess
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]

    def _git(*args):
        try:
            r = subprocess.run(["git", "-C", str(raiz), *args],
                               capture_output=True, text=True, timeout=8)
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    local = _git("rev-parse", "--short", "HEAD") or "desconocido"
    fecha = _git("log", "-1", "--format=%cd", "--date=short") or "?"
    rama = _git("rev-parse", "--abbrev-ref", "HEAD") or "?"

    remoto = "?"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as cliente:
            r = await cliente.get("https://api.github.com/repos/JULIANJUAREZMX01/KynicOS/commits/main")
            if r.status_code == 200:
                remoto = r.json()["sha"][:7]
    except Exception:
        remoto = "?"

    if remoto in ("?", local):
        estado = "no pude comprobar GitHub" if remoto == "?" else "estas en la ultima version"
    else:
        estado = f"hay una version nueva ({remoto}); corro /reiniciar tras actualizar"

    texto = (
        "<b>KYNIKOS · version</b>\n\n"
        f"Local: <code>{local}</code> ({fecha}, rama {rama})\n"
        f"Publicada: <code>{remoto}</code>\n"
        f"Estado: {estado}"
    )
    await update.message.reply_text(texto, parse_mode="HTML")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ficha tecnica del nodo, leida del sistema. Sin inventar."""
    from app.core.autoconocimiento import texto_para_usuario
    try:
        texto = texto_para_usuario()
    except Exception as e:
        logger.error(f"Error en /info: {e}")
        texto = "No pude leer mi configuracion del sistema."
    await update.message.reply_text(texto, parse_mode="HTML")



async def _enviar_respuesta(message, texto: str) -> None:
    """Envia la respuesta del modelo con formato.

    Los modelos locales contestan en Markdown y Telegram sin parse_mode lo
    muestra literal (### , **negrita**, [txt](url)). Se convierte a HTML de
    Telegram; si Telegram rechazara el HTML (etiqueta partida al trocear), se
    reenvia el trozo en texto plano para no perder nunca la respuesta.
    """
    from app.core.formato import md_a_html_telegram

    texto = texto or "…"
    for i in range(0, len(texto), 3500):
        trozo = texto[i:i + 3500]
        try:
            await message.reply_text(md_a_html_telegram(trozo), parse_mode="HTML")
        except Exception as e:
            logger.warning(f"HTML rechazado por Telegram, se envia en texto plano: {e}")
            await message.reply_text(trozo)

# ── Ecosistema de repositorios (solo lectura, solo el dueno) ────────────────

def _es_dueno(update: Update) -> bool:
    """Falla cerrado: sin TELEGRAM_USER_ID configurado, nadie pasa."""
    try:
        esperado = (Settings().telegram_user_id or "").strip()
        usuario = update.effective_user
        return bool(esperado and usuario and str(usuario.id) == esperado)
    except Exception:
        return False


async def ecosistema(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inventario de repositorios presentes en disco."""
    # Expone rutas locales: tambien se reserva al dueno, no solo buscar/leer.
    if not _es_dueno(update):
        await update.message.reply_text("Comando reservado al dueno del nodo.")
        return
    try:
        from app.core import ecosystem
        # estado() ya viene en HTML de Telegram: se envia tal cual.
        texto = ecosystem.estado()
    except Exception as e:
        logger.error(f"Error en /ecosistema: {e}", exc_info=True)
        texto = f"No pude leer el ecosistema: {str(e)[:120]}"
    try:
        await update.message.reply_text(texto[:4000], parse_mode="HTML")
    except Exception:
        await update.message.reply_text(texto[:4000])


async def ecosistema_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca texto en los repos permitidos."""
    if not _es_dueno(update):
        await update.message.reply_text("Comando reservado al dueno del nodo.")
        return
    patron = " ".join(context.args or []).strip()
    if len(patron) < 2:
        await update.message.reply_text("Uso: /ecosistema_buscar texto")
        return
    try:
        from app.core import ecosystem
        hallazgos = ecosystem.buscar(patron, max_resultados=10)
        if not hallazgos:
            texto = f"Sin hallazgos para: {patron}"
        else:
            lineas = [f"<b>KYNIKOS · busqueda</b> <code>{html.escape(patron)}</code>", ""]
            for h in hallazgos:
                ubicacion = f"{h['repo']}/{h['archivo']}:{h['linea']}"
                lineas.append(f"• <code>{html.escape(ubicacion)}</code>")
                lineas.append(html.escape((h['texto'] or '').strip())[:220])
            texto = "\n".join(lineas)
    except Exception as e:
        logger.error(f"Error en /ecosistema_buscar: {e}", exc_info=True)
        texto = f"No pude buscar: {str(e)[:120]}"
    await update.message.reply_text(texto[:4000], parse_mode="HTML")


async def ecosistema_leer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lee un archivo de texto permitido. El contenido va escapado dentro de <pre>."""
    if not _es_dueno(update):
        await update.message.reply_text("Comando reservado al dueno del nodo.")
        return
    if len(context.args or []) < 2:
        await update.message.reply_text("Uso: /ecosistema_leer repo ruta/archivo.md")
        return
    clave = context.args[0]
    ruta = " ".join(context.args[1:]).strip()
    try:
        from app.core import ecosystem
        contenido = ecosystem.leer(clave, ruta, max_bytes=2500)
        # Sin escapar, un '<' del archivo rompe el parseo de Telegram.
        texto = (f"<b>{html.escape(clave)}/{html.escape(ruta)}</b>\n\n"
                 f"<pre>{html.escape(contenido)}</pre>")
    except Exception as e:
        logger.error(f"Error en /ecosistema_leer: {e}", exc_info=True)
        texto = f"No pude leer: {html.escape(str(e))[:160]}"
    try:
        await update.message.reply_text(texto[:4000], parse_mode="HTML")
    except Exception:
        await update.message.reply_text(texto[:4000])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with agent loop."""
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        return

    logger.info(f"Message from {user.id}: {message.text[:50]}...")
    await message.chat.send_action("typing")

    try:
        # Respaldo por si el canal arranco sin parametros: se lee el registro
        # compartido, nunca `from app.main import`.
        from app.core.runtime import get_agent_loop, get_session_manager
        loop_vivo = _loop or get_agent_loop()
        sesiones_vivas = _sessions or get_session_manager()
        if not loop_vivo:
            logger.error("Mensaje sin agent loop: el canal arranco sin inyectarlo ni registrarlo")
            await message.reply_text("❌ Agent loop no iniciado")
            return
        if not sesiones_vivas:
            await message.reply_text("❌ Session manager no iniciado")
            return

        session_id = f"telegram_{user.id}"
        ctx = await sesiones_vivas.load_session(session_id)
        if not ctx:
            ctx = AgentContext(
                session_id=session_id,
                user_id=str(user.id),
                channel="telegram",
            )

        ctx.add_message("user", message.text)
        response = await loop_vivo.process_message(ctx)
        await sesiones_vivas.save_session(ctx)

        await _enviar_respuesta(message, response)
        logger.info(f"Response sent to {user.id}")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)[:100]}\n\nPor favor, intenta de nuevo.")


async def send_alert(message: str, settings: Settings) -> bool:
    """Send a proactive alert to the configured Telegram chat."""
    if not settings.telegram_user_id:
        logger.warning("Telegram alert skipped: telegram_user_id is not configured")
        return False
    if not _app or not _app.bot:
        logger.warning("Telegram alert skipped: bot is not initialized")
        return False
    try:
        await _app.bot.send_message(chat_id=settings.telegram_user_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")
        return False


async def _avisar_arranque(settings: Settings) -> None:
    """Avisa al jefe de que el nodo volvio, con commit y PID.

    Sirve para operar sin consola: tras /actualizar el proceso se reinicia solo,
    y este mensaje es la prueba de que volvio vivo. Si no llega, algo fallo y
    hay que mirar la PC.
    """
    import os
    import subprocess
    from pathlib import Path

    destino = settings.telegram_user_id or settings.tech_telegram_chat_id
    if not destino or not _app:
        return
    repo = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or "?"
    except Exception:
        commit = "?"
    try:
        await _app.bot.send_message(
            chat_id=int(destino),
            text=(f"🟢 <b>Nodo arriba</b>\n"
                  f"Commit: <code>{commit}</code>\n"
                  f"PID: <code>{os.getpid()}</code>\n"
                  f"Salida max: {settings.max_tokens_salida} tokens"),
            parse_mode="HTML",
        )
        logger.info("Aviso de arranque enviado al jefe")
    except Exception as e:
        logger.warning(f"No pude avisar del arranque: {e}")


async def start_telegram_bot(settings: Settings, agent_loop=None, session_manager=None) -> None:
    """Start Telegram bot."""
    global _app, _loop, _sessions
    _loop = agent_loop
    _sessions = session_manager
    if _loop is None:
        logger.warning("⚠️  Telegram arranca sin agent loop: los mensajes libres no podran responder")
    logger.info("🟢 Starting Telegram bot polling...")
    try:
        _app = Application.builder().token(settings.telegram_token).build()
        _app.add_handler(CommandHandler("start", start))
        _app.add_handler(CommandHandler("ayuda", ayuda))
        _app.add_handler(CommandHandler("help", ayuda))
        _app.add_handler(CommandHandler("estado", estado))
        _app.add_handler(CommandHandler("modelo", modelo))
        _app.add_handler(CommandHandler("logs", logs))
        _app.add_handler(CommandHandler("version", version))
        _app.add_handler(CommandHandler("instalar", instalar))
        _app.add_handler(CommandHandler("info", info))
        _app.add_handler(CommandHandler("ecosistema", ecosistema))
        _app.add_handler(CommandHandler("ecosistema_buscar", ecosistema_buscar))
        _app.add_handler(CommandHandler("ecosistema_leer", ecosistema_leer))
        _app.add_handler(CommandHandler("id", mi_id))
        _app.add_handler(CommandHandler("reiniciar", reiniciar))
        _app.add_handler(CommandHandler("actualizar", actualizar))
        _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await _app.initialize()
        await _app.start()
        if _app.updater is None:
            raise RuntimeError("Telegram updater is unavailable")
        await _app.updater.start_polling()
        global _arranque
        import time as _t
        _arranque = _t.time()
        logger.info("🟢 Telegram bot polling started")
        await _avisar_arranque(settings)
    except Exception as e:
        logger.error(f"Telegram bot error: {e}", exc_info=True)


async def stop_telegram_bot() -> None:
    """Stop Telegram bot and release updater/application resources."""
    global _app
    if not _app:
        return
    try:
        if _app.updater and _app.updater.running:
            await _app.updater.stop()
        if _app.running:
            await _app.stop()
        await _app.shutdown()
        logger.info("🛑 Telegram bot stopped")
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
    finally:
        _app = None
