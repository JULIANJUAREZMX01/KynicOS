"""Main agent loop - processes messages and executes tools"""

import asyncio
import json
import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.config import Settings
from app.utils import get_logger
from app.core.context import AgentContext, Message
from app.core.tools import ToolExecutor
from app.core import window
from app.cloud.providers import ProviderManager

logger = get_logger(__name__)


class AgentLoop:
    """Main agent loop for processing user messages"""

    def _max_salida(self) -> int:
        """Tokens maximos de salida.

        Ollama corre en la maquina del jefe, en CPU: a ~4 tokens por segundo un
        limite alto no mejora la respuesta, la convierte en minutos de silencio
        (y el default del proveedor era 8192). Se acota entre 64 y 1024 y se
        puede subir sin tocar codigo con KYNIKOS_MAX_SALIDA en el .env.
        """
        crudo = (os.getenv("KYNIKOS_MAX_SALIDA")
                 or getattr(self.settings, "max_tokens_salida", None))
        try:
            return max(64, min(1024, int(crudo)))
        except (TypeError, ValueError):
            return 320

    def __init__(self, settings: Settings, provider_manager: ProviderManager):
        self.settings = settings
        self.provider_manager = provider_manager
        self.tool_executor = ToolExecutor()

    async def process_message(self, ctx: AgentContext) -> str:
        """
        Process user message and generate response
        
        Args:
            ctx: AgentContext with user message
            
        Returns:
            Response text
        """
        try:
            # Get LLM provider
            provider = self.provider_manager.get_provider()
            logger.info(f"Using provider: {provider.__class__.__name__}")

            # Prepare messages for LLM
            messages = self._format_messages(ctx)

            # Call LLM
            limite = self._max_salida()
            logger.info(f"Calling LLM with {len(messages)} messages (max {limite} tokens de salida)")
            t0 = time.monotonic()
            llm_response = await provider.call(messages, max_tokens=limite)
            logger.info(f"LLM respondio en {time.monotonic() - t0:.1f}s")

            # Parse response
            response_text = llm_response.get("text", "")
            tool_calls = llm_response.get("tool_calls", [])

            # Execute tools if needed
            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool calls")
                for tool_call in tool_calls:
                    tool_result = await self.tool_executor.execute(tool_call)
                    ctx.add_message("tool", tool_result, metadata={"tool": tool_call.get("name")})

            # Add assistant response
            ctx.add_message("assistant", response_text)
            logger.info("Message processed successfully")

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            tipo = type(e).__name__
            if "Timeout" in tipo or "timeout" in str(e).lower():
                error_msg = ("⏳ El modelo local no respondió a tiempo. "
                             "Sigue vivo, pero el equipo va lento: prueba con algo más corto "
                             "o baja KYNIKOS_MAX_SALIDA en el .env.")
                logger.error("Timeout del LLM: el modelo local no respondio a tiempo")
            else:
                error_msg = f"Disculpa, ocurrió un error: {str(e)[:100]}"
            ctx.add_message("assistant", error_msg, metadata={"error": True})
            return error_msg

    def _format_messages(self, ctx: AgentContext) -> List[Dict[str, str]]:
        """Format context messages for LLM API

        El historial se recorta segun el proveedor. Ollama corre en la maquina
        con 4096 tokens de contexto: mandarle 20 mensajes lo satura y la
        llamada muere con "Error processing message". En la nube cabe mas, asi
        que recortar siempre empeoraria las respuestas sin necesidad.
        """
        formatted = []

        # Add system prompt
        system_prompt = self._build_system_prompt(ctx)
        formatted.append({"role": "system", "content": system_prompt})

        # Cuantos mensajes caben segun quien responda
        try:
            proveedor = self.provider_manager.get_provider().__class__.__name__
        except Exception:
            proveedor = ""
        limite = window.limite_historial(proveedor)

        # Add conversation history, con ventana deslizante
        historial, fuera = window.recortar(ctx.messages, limite)
        if fuera:
            logger.info(
                f"Historial recortado para {proveedor or 'proveedor desconocido'}: "
                f"{fuera} mensajes fuera, se envian {len(historial)}"
            )

        for msg in historial:
            formatted.append({"role": msg.role, "content": msg.content})

        return formatted

    def _build_system_prompt(self, ctx: AgentContext) -> str:
        """Build system prompt with context information"""
        prompt = """Eres Nanobot, asistente personal de desarrollo de QUINTANA (Julian Juarez).

## Tu Rol
- Senior developer assistant
- Especialista en: Python, JavaScript, DevOps, cloud deployment
- Acceso a herramientas: shell, files, git, web

## Comunicación
- Siempre en español
- Breve y al grano (máximo 4 líneas salvo que pida detalle)
- Técnico y directo
- Muestra output real de comandos

## Herramientas Disponibles
Puedes usar:
- execute_shell(command) → output
- read_file(path) → content
- write_file(path, content)
- git_operation(cmd)
- web_fetch(url)

Llama herramientas cuando sea necesario para ayudar."""

        # Add user context if available
        if hasattr(ctx, 'user_id'):
            prompt += f"\n\nUsuario: {ctx.user_id}"
        if hasattr(ctx, 'channel'):
            prompt += f"\nCanal: {ctx.channel}"

        return prompt

    async def handle_tool_response(self, tool_response: str, ctx: AgentContext) -> str:
        """Handle tool response and generate follow-up"""
        try:
            # Add tool response to context
            ctx.add_message("tool", tool_response)

            # Get provider and call LLM again
            provider = self.provider_manager.get_provider()
            messages = self._format_messages(ctx)

            llm_response = await provider.call(messages)
            response_text = llm_response.get("text", "")

            ctx.add_message("assistant", response_text)
            return response_text

        except Exception as e:
            logger.error(f"Error handling tool response: {e}")
            return f"Error procesando respuesta de herramienta: {str(e)[:100]}"
