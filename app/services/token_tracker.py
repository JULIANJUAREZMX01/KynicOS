from collections import defaultdict
from loguru import logger


class TokenTracker:
    """Track token usage and rate limits per provider"""

    def __init__(self):
        self.usage: dict = defaultdict(lambda: {
            "tokens_used": 0,
            "requests_made": 0,
        })

        self.limit_per_minute = {
            "anthropic": 50000,
            "groq": 30000,
            "openai": 90000,
            "ollama": float('inf'),
        }

        self.logger = logger

    def add_usage(self, provider: str, tokens_used: int, requests: int = 1):
        """Record token/request usage"""
        self.usage[provider]["tokens_used"] += tokens_used
        self.usage[provider]["requests_made"] += requests
        self.logger.debug(f"{provider}: +{tokens_used} tokens")

    def is_rate_limited(self, provider: str) -> bool:
        """Check if provider exceeds 90% of rate limit"""
        if provider not in self.limit_per_minute:
            return False

        tokens_used = self.usage[provider]["tokens_used"]
        limit = self.limit_per_minute[provider]

        if limit == float('inf'):
            return False

        return tokens_used >= (limit * 0.9)

    def get_remaining(self, provider: str) -> int:
        """Get remaining tokens before rate limit"""
        limit = self.limit_per_minute.get(provider, float('inf'))
        used = self.usage[provider]["tokens_used"]

        if limit == float('inf'):
            return int(1e9)

        return max(0, int(limit - used))

    def reset_minute(self, provider: str):
        """Reset counters for new minute"""
        self.usage[provider]["tokens_used"] = 0
        self.usage[provider]["requests_made"] = 0
        self.logger.info(f"{provider} counters reset")
