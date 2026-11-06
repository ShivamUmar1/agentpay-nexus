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
    GEMINI_MODEL: str = "gemini-3.8-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # PayPal Integration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # sandbox or live
    PAYPAL_API_BASE: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        origins = [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        # Allow all if wildcard is specified or in local dev
        if "*" in origins:
            return ["*"]
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
    def ai_provider_status(self) -> str:
        if self.GEMINI_API_KEY:
            return "gemini"
        elif self.OPENAI_API_KEY:
            return "openai"
        return "deterministic_fallback"


settings = Settings()
