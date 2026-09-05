"""Telegram bot integration for KynicOS with Agent Loop."""

from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.config import Settings
from app.utils import get_logger
from app.core.context import AgentContext

logger = get_logger(__name__)
_app: Optional[Application] = None


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
        _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await _app.initialize()
        await _app.start()
        if _app.updater is None:
            raise RuntimeError("Telegram updater is unavailable")
        await _app.updater.start_polling()
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
