"""KynicOS — Pydantic Settings"""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    persona: str = "kynicos"

    hotel_name: str = "Hotel Cancún"
    hotel_location: str = "Cancún, México"
    hotel_currency: str = "USD"
    hotel_timezone: str = "America/Mexico_City"

    telegram_token: str = ""
    telegram_user_id: str = ""
    tech_telegram_chat_id: Optional[str] = None

    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-opus-4-5"
    openai_api_key: Optional[str] = None

    # ── Local LLM ─────────────────────────────────────────────
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_num_ctx: int = 4096   # ventana de contexto acotada: menos RAM en KV cache
    max_tokens_salida: int = 320  # ~4 tok/s en CPU: 768 eran minutos de silencio
    timeout_llm: float = 300.0    # segundos; un modelo local lento necesita margen
    # ── Autenticación local de dos pasos ──────────────────────
    # El instalador escribe estas dos claves en .env. Sin declararlas aquí,
    # pydantic-settings lanza extra_forbidden y el nodo no arranca.
    kynikos_palabra_1: str = ""      # palabra del primer paso
    kynikos_palabra_2: str = ""      # palabra del segundo paso (opcional)
    kynikos_estado_dir: str = ".kynikos"  # estado, bloqueos e intentos fallidos
    # Token de la API de estado. Sin el, /api/status falla cerrado (503).
    kynikos_api_token: str = ""

    telegram_webhook_secret: str = ""  # valida el webhook de Telegram en serverless
    public_base_url: str = ""  # URL publica, necesaria para registrar el webhook

    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "+14155238886"
    twilio_whatsapp_to: Optional[str] = None

    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_hotel_account_id: Optional[str] = None
    stripe_nexus_account_id: Optional[str] = None
    stripe_commission_percentage: int = 5

    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: Optional[str] = None

    sentinel_enabled: bool = True
    log_check_interval: int = 5
    alert_on_failure: bool = True
    auto_healing_enabled: bool = False

    environment: str = "production"
    log_level: str = "INFO"
    port: int = 8000
    host: str = "0.0.0.0"

    @field_validator("max_tokens_salida", mode="after")
    @classmethod
    def _salida_heredada(cls, valor: int) -> int:
        """768 es el default de la version anterior y en CPU son minutos de silencio.

        Si el .env todavia lo trae se reduce a 320; cualquier otro valor se
        respeta tal cual, y KYNIKOS_MAX_SALIDA sigue mandando por encima.
        """
        return 320 if valor == 768 else valor

    class Config:
        env_file = ".env"
        case_sensitive = False
