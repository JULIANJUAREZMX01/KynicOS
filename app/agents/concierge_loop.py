"""
KynicOS — Concierge Agent Loop
El cerebro principal del sistema. Extiende el AgentLoop base de nanobot-cloud
con skills específicos de hospitalidad:
  - HVAC Triage
  - MueveCancún transport routing
  - Stripe payment triggers (stub, para conectar en Fase 2)
  - Telegram escalation (mantenimiento → técnico)
"""

import asyncio
from typing import Optional, Dict, Any

from app.core.loop import AgentLoop
from app.core.context import AgentContext
from app.cloud.providers import ProviderManager
from app.concierge.persona import get_persona, Persona, LEO
from app.skills.hvac_triage import detect_hvac_issue, generate_hvac_response, get_ticket_priority
from app.skills.mueve_cancun import is_transport_query, get_route_info, format_route_response, get_generic_transport_response
from app.config import Settings
from app.utils import get_logger

logger = get_logger(__name__)


class ConciergeAgentLoop(AgentLoop):
    """
    Extiende AgentLoop con lógica específica de concierge hotelero.
    Antes de pasar al LLM, verifica si hay skills que pueden responder directo.
    """

    def __init__(self, settings: Settings, provider_manager: ProviderManager,
                 persona: Optional[Persona] = None):
        super().__init__(settings, provider_manager)
        self.persona = persona or LEO
        logger.info(f"🏨 ConciergeAgentLoop iniciado — Persona: {self.persona.name}")

    async def process_message(self, ctx: AgentContext) -> str:
        """
        Procesa el mensaje con pipeline:
        1. Skill HVAC → respuesta inmediata si es reporte técnico
        2. Skill MueveCancún → respuesta de transporte si aplica
        3. LLM con system prompt del persona → respuesta general
        """
        if not ctx.messages:
            return self.persona.greeting

        last_message = ctx.messages[-1].content if ctx.messages else ""
        logger.info(f"[{self.persona.name}] Procesando: {last_message[:60]}...")

        # ── Skill 1: HVAC Triage ─────────────────────────────
        symptom_key, issue_data = detect_hvac_issue(last_message)
        if symptom_key:
            room = getattr(ctx, 'room_number', 'su habitación')
            response = generate_hvac_response(symptom_key, issue_data, room)
            
            # Escalar a técnico via Telegram si prioridad alta/media
            priority = get_ticket_priority(symptom_key)
            if priority in ("alta", "media"):
                await self._escalate_maintenance_ticket(ctx, symptom_key, issue_data, priority)
            
            logger.info(f"[HVAC] Skill activado — síntoma: {symptom_key}, prioridad: {priority}")
            ctx.add_message("assistant", response)
            return response

        # ── Skill 2: Transporte MueveCancún ──────────────────
        if is_transport_query(last_message):
            route_info = get_route_info(last_message)
            if route_info:
                response = format_route_response(route_info)
            else:
                response = get_generic_transport_response()
            
            logger.info(f"[MueveCancún] Skill de transporte activado")
            ctx.add_message("assistant", response)
            return response

        # ── LLM: Respuesta general con persona ────────────────
        return await super().process_message(ctx)

    def _build_system_prompt(self, ctx: AgentContext) -> str:
        """Usa el system prompt de la persona activa"""
        return self.persona.system_prompt

    async def _escalate_maintenance_ticket(
        self, ctx: AgentContext, symptom_key: str, 
        issue_data: Dict, priority: str
    ):
        """
        Escala ticket de mantenimiento al técnico via Telegram.
        En Fase 2 también crea ticket en PostgreSQL y notifica al manager.
        """
        try:
            room = getattr(ctx, 'room_number', 'desconocida')
            guest_name = getattr(ctx, 'guest_name', 'Huésped')
            
            ticket_msg = (
                f"🔧 *TICKET MANTENIMIENTO*\n"
                f"Prioridad: {'🔴 ALTA' if priority == 'alta' else '🟡 MEDIA'}\n"
                f"Habitación: {room}\n"
                f"Huésped: {guest_name}\n"
                f"Problema: {issue_data.get('descripcion', symptom_key)}\n"
                f"ETA: {issue_data.get('eta_minutos', 30)} min\n\n"
                f"Diagnóstico probable:\n{issue_data['diagnostico'][0]}"
            )
            
            # Enviar a Telegram del técnico (configurado en settings)
            await self._send_telegram_alert(ticket_msg)
            logger.info(f"[Escalation] Ticket enviado — hab {room}, prioridad {priority}")
            
        except Exception as e:
            logger.error(f"[Escalation] Error al escalar: {e}")

    async def _send_telegram_alert(self, message: str):
        """Envía alerta al chat de Telegram del técnico/manager"""
        try:
            from telegram import Bot
            telegram_token = self.settings.telegram_token
            # El chat_id de notificaciones técnicas (configurar en .env como TECH_TELEGRAM_CHAT_ID)
            tech_chat_id = getattr(self.settings, 'tech_telegram_chat_id', None)
            
            if telegram_token and tech_chat_id:
                bot = Bot(token=telegram_token)
                await bot.send_message(
                    chat_id=tech_chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info(f"✅ Alerta Telegram enviada a chat {tech_chat_id}")
            else:
                logger.warning("⚠️ TECH_TELEGRAM_CHAT_ID no configurado — escalation omitida")
        except Exception as e:
            logger.error(f"Telegram alert error: {e}")
