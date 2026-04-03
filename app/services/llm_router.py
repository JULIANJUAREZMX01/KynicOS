import asyncio
from typing import Optional, Dict
from enum import Enum
from loguru import logger
from app.services.token_tracker import TokenTracker


class ProviderName(str, Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OPENAI = "openai"


class LLMRouter:
    # Priority order: External providers first, then Ollama as fallback
    PRIORITY_ORDER = [
        ProviderName.ANTHROPIC,
        ProviderName.GROQ,
        ProviderName.OPENAI,
        ProviderName.OLLAMA,
    ]

    def __init__(self):
        self.providers: Dict[str, Dict] = {}
        self.current_provider: Optional[str] = None
        self.logger = logger
        self.token_tracker = TokenTracker()
        self._reset_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize all providers"""
        self.providers = {
            "ollama": {"status": "available", "url": "http://localhost:11434"},
            "anthropic": {"status": "available", "url": "https://api.anthropic.com"},
            "groq": {"status": "available", "url": "https://api.groq.com"},
            "openai": {"status": "available", "url": "https://api.openai.com"},
        }
        self.logger.info("LLMRouter initialized")
        # Start periodic reset so providers become available again each minute
        if not self._reset_task:
            self._reset_task = asyncio.create_task(self._reset_token_counters())

    async def _reset_token_counters(self):
        """Periodically reset token counters every 60 seconds"""
        while True:
            await asyncio.sleep(60)
            for provider in list(self.providers.keys()):
                self.token_tracker.reset_minute(provider)
            self.logger.debug("Token counters reset for all providers")

    def stop(self):
        """Cancel background tasks started by this router"""
        if self._reset_task and not self._reset_task.done():
            self._reset_task.cancel()
            self._reset_task = None

    async def select_provider(self) -> str:
        """Select best available provider based on priority and rate limits"""
        for provider_name in self.PRIORITY_ORDER:
            name = provider_name.value
            if name in self.providers:
                # Check if provider is available
                provider = self.providers[name]
                if provider.get("status") != "available":
                    continue

                # Check rate limits. Ollama is configured with an infinite limit,
                # so TokenTracker's is_rate_limited() will never flag it as limited.
                if self.token_tracker.is_rate_limited(name):
                    self.logger.warning(f"Provider {name} is rate limited (>90%). Skipping.")
                    continue

                self.current_provider = name
                return name

        # All primary providers unavailable or limited; fall back to Ollama if it is available.
        ollama_name = ProviderName.OLLAMA.value
        ollama_provider = self.providers.get(ollama_name)
        if not ollama_provider or ollama_provider.get("status") != "available":
            self.logger.error("All providers unavailable or limited, including Ollama.")
        else:
            self.logger.warning("All primary providers unavailable or limited. Falling back to Ollama.")
        return ollama_name

    async def call_llm(self, prompt: str) -> str:
        """Route LLM call to selected provider"""
        provider = await self.select_provider()
        self.logger.info(f"Routing to {provider}: {prompt[:50]}...")

        # Note: In a real implementation, usage should be recorded after the call.
        # self.token_tracker.add_usage(provider, tokens_used)

        return f"Response from {provider}"
