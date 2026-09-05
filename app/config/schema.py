"""KynicOS — Pydantic Settings"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    persona: str = "leo"

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

    class Config:
        env_file = ".env"
        case_sensitive = False
