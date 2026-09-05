"""LLM Provider management - Groq → Anthropic → Ollama local."""

import asyncio
from typing import List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.utils import get_logger

logger = get_logger(__name__)


class GroqProvider:
    """Groq LLM provider (primary)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        self.name = "groq"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call(self, messages: List[Dict[str, str]], max_tokens: int = 8192, temperature: float = 0.7) -> Dict[str, Any]:
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            return {"text": content, "tool_calls": []}
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise


class AnthropicProvider:
    """Anthropic Claude provider (fallback)."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-5"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.name = "anthropic"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call(self, messages: List[Dict[str, str]], max_tokens: int = 8192, temperature: float = 0.7) -> Dict[str, Any]:
        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            content = response.content[0].text if response.content else ""
            return {"text": content, "tool_calls": []}
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise


class OllamaProvider:
    """Local Ollama provider; no cloud credentials required."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = "ollama"

    async def call(self, messages: List[Dict[str, str]], max_tokens: int = 8192, temperature: float = 0.7) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        content = data.get("message", {}).get("content", "")
        return {"text": content, "tool_calls": []}


class ProviderManager:
    """Manage cloud providers with a local Ollama fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers = []
        self._init_providers()

    def _init_providers(self):
        if self.settings.groq_api_key:
            try:
                self.providers.append(GroqProvider(self.settings.groq_api_key, self.settings.groq_model))
                logger.info("✅ Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")

        if self.settings.anthropic_api_key:
            try:
                self.providers.append(AnthropicProvider(self.settings.anthropic_api_key, self.settings.anthropic_model))
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        self.providers.append(OllamaProvider(self.settings.ollama_url, self.settings.ollama_model))
        logger.info("✅ Ollama local provider configured as final fallback")

    def get_provider(self):
        if not self.providers:
            raise RuntimeError("No LLM providers available")
        return self.providers[0]

    async def call(self, messages: List[Dict[str, str]], max_tokens: int = 8192, temperature: float = 0.7) -> Dict[str, Any]:
        """Try each provider in priority order until one succeeds."""
        errors = []
        for provider in self.providers:
            try:
                return await provider.call(messages, max_tokens, temperature)
            except Exception as e:
                logger.error(f"{provider.name} failed: {e}")
                errors.append(f"{provider.name}: {str(e)[:120]}")
        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))
