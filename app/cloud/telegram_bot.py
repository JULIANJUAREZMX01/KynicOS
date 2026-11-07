"""Telegram bot integration for KynicOS with Agent Loop."""

from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.config import Settings
from app.utils import get_logger
from app.core.context import AgentContext

logger = get_logger(__name__)
_app: Optional[Application] = None
_arranque: Optional[float] = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start using the configured KynicOS persona."""
    user = update.effective_user
    message = update.message
    if not message:
        return

    try:
        import os
        from app.concierge.persona import get_persona
        persona = get_persona(os.getenv("PERSONA", "leo"))
        greeting = persona.greeting
    except Exception:
        greeting = "Soy KynicOS, tu asistente. ¿En qué puedo ayudarte?"

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
        "/reiniciar  — reinicia el bot sin matar el proceso\n"
        "/ayuda  — esta lista\n\n"
        "Cualquier otro mensaje lo responde el agente."
    )
    await update.message.reply_text(texto, parse_mode="HTML")


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
            "No reinicio el updater desde aqui a proposito: hacerlo cancela la tarea "
            "que atiende este mensaje y el bot queda mudo hasta reiniciar el proceso.\n"
            "Para un reinicio real, en la PC:\n"
            "  .\\nodo\\kynikos.ps1 reiniciar"
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with agent loop."""
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        return

    logger.info(f"Message from {user.id}: {message.text[:50]}...")
    await message.chat.send_action("typing")

    try:
        from app.main import _agent_loop, _session_manager
        if not _agent_loop:
            await message.reply_text("❌ Agent loop no iniciado")
            return
        if not _session_manager:
            await message.reply_text("❌ Session manager no iniciado")
            return

        session_id = f"telegram_{user.id}"
        ctx = await _session_manager.load_session(session_id)
        if not ctx:
            ctx = AgentContext(
                session_id=session_id,
                user_id=str(user.id),
                channel="telegram",
            )

        ctx.add_message("user", message.text)
        response = await _agent_loop.process_message(ctx)
        await _session_manager.save_session(ctx)

        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await message.reply_text(response[i:i + 4096])
        else:
            await message.reply_text(response)
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


async def start_telegram_bot(settings: Settings) -> None:
    """Start Telegram bot."""
    global _app
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
        _app.add_handler(CommandHandler("id", mi_id))
        _app.add_handler(CommandHandler("reiniciar", reiniciar))
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
