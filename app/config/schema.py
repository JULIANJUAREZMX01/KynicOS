"""KynicOS — Pydantic Settings"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ── Persona ──────────────────────────────────────────────
    persona: str = "leo"  # leo | nexus | mueve

    # ── Hotel Config ─────────────────────────────────────────
    hotel_name: str = "Hotel Cancún"
    hotel_location: str = "Cancún, México"
    hotel_currency: str = "USD"
    hotel_timezone: str = "America/Mexico_City"

    # ── Telegram ─────────────────────────────────────────────
    telegram_token: str
    telegram_user_id: str = ""
    # Chat ID del técnico de mantenimiento (para escalación HVAC)
    tech_telegram_chat_id: Optional[str] = None

    # ── LLM Providers ────────────────────────────────────────
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-5"
    openai_api_key: Optional[str] = None

    # ── WhatsApp (Twilio) ────────────────────────────────────
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "+14155238886"
    twilio_whatsapp_to: Optional[str] = None

    # ── Stripe (Fase 2) ──────────────────────────────────────
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_hotel_account_id: Optional[str] = None
    stripe_nexus_account_id: Optional[str] = None
    stripe_commission_percentage: int = 5

    # ── Database (Fase 2) ────────────────────────────────────
    database_url: Optional[str] = None
    redis_url: Optional[str] = None

    # ── AWS S3 ───────────────────────────────────────────────
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: Optional[str] = None

    # ── App ──────────────────────────────────────────────────
    environment: str = "production"
    log_level: str = "INFO"
    port: int = 8000
    host: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = False
