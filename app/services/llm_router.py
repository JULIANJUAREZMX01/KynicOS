import asyncio
import os
from typing import Optional, Dict
from enum import Enum
from loguru import logger
from app.services.token_tracker import TokenTracker


class ProviderName(str, Enum):
    AMD_VLLM = "amd_vllm"
    OLLAMA = "ollama"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class LLMRouter:
    """
    KynicOS LLM Router — AMD-first
    Priority: AMD MI300X (vLLM) → Ollama → Groq → Anthropic → OpenAI
    
    Para activar AMD: set AMD_VLLM_URL en variables de entorno de Render.
    Para activar Ollama: set OLLAMA_URL (ej: http://localhost:11434).
    """

    PRIORITY_ORDER = [
        ProviderName.AMD_VLLM,
        ProviderName.OLLAMA,
        ProviderName.GROQ,
        ProviderName.ANTHROPIC,
        ProviderName.OPENAI,
    ]

    def __init__(self):
        self.providers: Dict[str, Dict] = {}
        self.current_provider: Optional[str] = None
        self.logger = logger
        self.token_tracker = TokenTracker()
        self._reset_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize all providers — AMD MI300X primero si está disponible."""
        amd_url = os.getenv("AMD_VLLM_URL", "")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        self.providers = {
            "amd_vllm": {
                "status": "available" if amd_url else "disabled",
                "url": amd_url or "",
                "model": os.getenv("AMD_VLLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
                "cost_per_token": 0.0,
                "note": "AMD MI300X — costo cero por token",
            },
            "ollama": {
                "status": "available" if os.getenv("OLLAMA_URL") else "disabled",
                "url": ollama_url,
                "model": os.getenv("OLLAMA_MODEL", "llama3.1:70b"),
                "cost_per_token": 0.0,
                "note": "Ollama local",
            },
            "groq": {
                "status": "available" if os.getenv("GROQ_API_KEY") else "disabled",
                "url": "https://api.groq.com/openai/v1",
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "note": "Groq free tier — fallback primario",
            },
            "anthropic": {
                "status": "available" if os.getenv("ANTHROPIC_API_KEY") else "disabled",
                "url": "https://api.anthropic.com",
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                "note": "Anthropic — fallback secundario",
            },
            "openai": {
                "status": "available" if os.getenv("OPENAI_API_KEY") else "disabled",
                "url": "https://api.openai.com/v1",
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "note": "OpenAI — fallback terciario",
            },
        }

        active = [k for k, v in self.providers.items() if v["status"] == "available"]
        self.logger.info(f"LLMRouter initialized. Active providers: {active}")

        if not self._reset_task:
            self._reset_task = asyncio.create_task(self._reset_token_counters())

    async def _reset_token_counters(self):
        while True:
            await asyncio.sleep(60)
            for provider in list(self.providers.keys()):
                self.token_tracker.reset_minute(provider)
            self.logger.debug("Token counters reset")

    def stop(self):
        if self._reset_task and not self._reset_task.done():
            self._reset_task.cancel()
            self._reset_task = None

    async def select_provider(self) -> str:
        """Select best available provider by priority."""
        for provider_name in self.PRIORITY_ORDER:
            name = provider_name.value
            provider = self.providers.get(name, {})

            if provider.get("status") != "available":
                continue

            if self.token_tracker.is_rate_limited(name):
                self.logger.warning(f"Provider {name} rate limited. Skipping.")
                continue

            self.current_provider = name
            self.logger.debug(f"Selected provider: {name} ({provider.get(\"model\",\"\")})")
            return name

        # Last resort: Ollama even if disabled (local fallback)
        self.logger.error("All providers unavailable or rate-limited!")
        raise RuntimeError("No LLM provider available. Check API keys and AMD_VLLM_URL.")

    async def get_provider_info(self, name: str) -> Dict:
        """Get provider config including model name and URL."""
        return self.providers.get(name, {})

    def get_status(self) -> Dict:
        """Status dict for /api/status endpoint."""
        return {
            "current": self.current_provider,
            "providers": {
                k: {"status": v["status"], "model": v.get("model",""), "note": v.get("note","")}
                for k, v in self.providers.items()
            },
        }

