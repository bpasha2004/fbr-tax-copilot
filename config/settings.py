from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Literal
import os


class Settings(BaseSettings):

    # Environment
    ENV: Literal["development", "production"] = "development"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:8000"
    TRUST_PROXY_HEADERS: bool = False
    MAX_PAYLOAD_BYTES: int = 1_048_576

    # AI Provider
    AI_PROVIDER: Literal["ollama", "gemini", "claude", "local"] = "ollama"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    EMBEDDING_PROVIDER: Literal["ollama", "local"] = "ollama"
    LOCAL_EMBEDDING_DIM: int = 384
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8001
    PAYMENT_MODE: Literal["live", "sandbox"] = "sandbox"
    PAYMENT_DEFAULT_CURRENCY: str = "PKR"
    PAYMENT_HTTP_TIMEOUT_SECONDS: float = 15.0
    PAYMENT_MAX_RETRIES: int = 5
    JAZZCASH_API_BASE_URL: str = ""
    EASYPAISA_API_BASE_URL: str = ""
    RAAST_API_BASE_URL: str = ""
    JAZZCASH_API_KEY: str = ""
    JAZZCASH_API_SECRET: str = ""
    EASYPAISA_API_KEY: str = ""
    EASYPAISA_API_SECRET: str = ""
    RAAST_API_KEY: str = ""
    RAAST_API_SECRET: str = ""
    OLLAMA_MODEL: str = "qwen2.5:3b"
    GEMINI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""

    # Vector DB
    VECTOR_DB: Literal["chromadb", "qdrant"] = "chromadb"
    CHROMADB_PATH: str = "./data/chromadb"
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite:///./data/fbr_dev.db"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Auth
    AUTH_MODE: Literal["api_key", "oauth2"] = "api_key"
    SESSION_TTL_HOURS: int = 8
    REQUIRE_MFA_FOR_WRITES: bool = True
    API_KEY: str = "dev-key-change-in-production"
    BOOTSTRAP_ADMIN_EMAILS: str = ""

    # Security
    SECRET_KEY: str = "dev-secret-change-in-production"

    # Google OIDC (Gmail Sign-In) — free, no cost
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    # Payment config — domestic wallets (no gateway fees)
    JAZZCASH_MSISDN: str = ""
    JAZZCASH_MERCHANT_ID: str = ""
    EASYPAISA_MSISDN: str = ""
    EASYPAISA_MERCHANT_ID: str = ""
    RAAST_IBAN: str = ""
    RAAST_BANK_NAME: str = ""
    RAAST_ACCOUNT_NAME: str = "FBR Tax Advisory Services"
    BANK_IBAN: str = ""
    BANK_NAME: str = ""
    BANK_ACCOUNT_NAME: str = "FBR Tax Advisory Services"
    BANK_SWIFT: str = ""

    # Payment webhook signing secrets
    JAZZCASH_WEBHOOK_SECRET: str = ""
    EASYPAISA_WEBHOOK_SECRET: str = ""
    RAAST_WEBHOOK_SECRET: str = ""

    # Rules Engine
    RULES_DIR: str = "./rules_engine/rules"
    FBR_FINANCE_ACT_2026_SHA256: str = ""
    REQUIRE_CA_VALIDATION: bool = True  # Fail closed until rules are verified
    APP_VERSION: str = "4.0.0"

    model_config = SettingsConfigDict(
        env_file=("config/.env.prod" if os.getenv("ENV") == "production" else "config/.env.dev"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENV == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if self.API_KEY in {"dev-key-change-in-production", "CHANGE_ME", ""}:
                raise ValueError("Set a strong API_KEY before starting in production")
            if self.SECRET_KEY in {"dev-secret-change-in-production", "CHANGE_ME", ""}:
                raise ValueError("Set a strong SECRET_KEY before starting in production")
            if not self.CORS_ORIGINS.strip():
                raise ValueError("Set CORS_ORIGINS before starting in production")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL, not SQLite")
            if not self.REDIS_URL:
                raise ValueError("Production requires REDIS_URL")
            if self.PAYMENT_MODE == "live":
                for provider in ("JAZZCASH", "EASYPAISA", "RAAST"):
                    if not getattr(self, f"{provider}_API_BASE_URL"):
                        raise ValueError(f"{provider}_API_BASE_URL is required in live payment mode")
                    if not getattr(self, f"{provider}_API_KEY") or not getattr(self, f"{provider}_API_SECRET"):
                        raise ValueError(f"{provider} API credentials are required in live payment mode")
                    if not getattr(self, f"{provider}_WEBHOOK_SECRET"):
                        raise ValueError(f"{provider}_WEBHOOK_SECRET is required in live payment mode")
            if self.REQUIRE_CA_VALIDATION and not self.FBR_FINANCE_ACT_2026_SHA256:
                raise ValueError("Pin FBR_FINANCE_ACT_2026_SHA256 before production startup")
        return self


settings = Settings()