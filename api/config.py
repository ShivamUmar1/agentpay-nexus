import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AgentPay Nexus"
    APP_ENV: str = "production"
    DEBUG: bool = False
    APP_BASE_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Database: defaults to local sqlite for development / testing, supports Postgres / Supabase
    DATABASE_URL: str = "sqlite:///./agentpay.db"

    # Supabase (optional for hosted auth and database)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # AI Providers
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODEL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT: float = 12.0
    ENABLE_LIVE_AI_DIAGNOSTICS: bool = False

    # PayPal Integration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_API_BASE: Optional[str] = None

    # Anonymous Guest Identity & Session Security
    GUEST_SESSION_SECRET: Optional[str] = None
    GUEST_SESSION_COOKIE_NAME: str = "agentpay_guest_session"
    GUEST_SESSION_EXPIRY_DAYS: int = 7

    # Distributed Rate Limiting & Resource Protection
    RATE_LIMIT_GUEST_TASKS_PER_HOUR: int = 2
    RATE_LIMIT_IP_TASKS_PER_HOUR: int = 10
    RATE_LIMIT_ACTIVE_TASKS_PER_SESSION: int = 2
    RATE_LIMIT_GUEST_STEPS_PER_HOUR: int = 20
    RATE_LIMIT_IP_STEPS_PER_HOUR: int = 60
    MAX_REQUEST_BODY_BYTES: int = 32768
    IP_HASH_SALT: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        base_trusted = [
            "https://agentpay-nexus.vercel.app",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ]
        if not self.CORS_ORIGINS:
            return base_trusted
        origins = [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip() and orig.strip() != "*"]
        for bt in base_trusted:
            if bt not in origins:
                origins.append(bt)
        return origins

    @property
    def paypal_endpoint(self) -> str:
        if self.PAYPAL_API_BASE:
            return self.PAYPAL_API_BASE
        if self.PAYPAL_MODE.lower() == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @property
    def has_paypal_credentials(self) -> bool:
        return bool(self.PAYPAL_CLIENT_ID and self.PAYPAL_CLIENT_SECRET)

    @property
    def is_hosted(self) -> bool:
        """Determines if running in any hosted serverless environment (Vercel, AWS Lambda, etc.)."""
        vercel_flag = (os.environ.get("VERCEL") or "").strip().lower()
        vercel_env = (os.environ.get("VERCEL_ENV") or "").strip().lower()
        lambda_name = (os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or "").strip()
        return bool(vercel_flag in ("1", "true") or vercel_env or lambda_name)

    @property
    def is_production(self) -> bool:
        """Determines if the runtime environment must enforce production-grade lockout.
        Fails closed:
        - Any hosted deployment (Vercel Production, Vercel Preview, or Lambda) always fails closed.
        - Any environment other than explicitly lowercase 'development' or 'test' running locally
          fails closed.
        """
        if self.is_hosted:
            return True

        app_env = (self.APP_ENV or "").lower().strip()
        if app_env in ("development", "test", "dev", "local"):
            return False

        return True

    @property
    def guest_session_secret(self) -> Optional[str]:
        """Resolves guest session secret.
        Fails closed in production/hosted environments: returns None if not explicitly configured.
        In local dev/testing: falls back to a deterministic local test secret if not explicitly configured.
        """
        if self.GUEST_SESSION_SECRET and self.GUEST_SESSION_SECRET.strip():
            return self.GUEST_SESSION_SECRET.strip()
        if self.is_production:
            return None
        return "local-dev-guest-session-secret-deterministic-not-for-production"

    @property
    def ai_provider_status(self) -> str:
        if self.GEMINI_API_KEY:
            return "gemini"
        elif self.OPENAI_API_KEY:
            return "openai"
        return "deterministic_fallback"


settings = Settings()
