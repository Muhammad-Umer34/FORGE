# D:\FYP\FORGE-1\backend\core\config.py
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Single .env at the FORGE-1 root, loaded by path so the working directory does not matter
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class Settings:
    PROJECT_NAME: str = "FORGE-1 AI Website Builder Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Model provider (D-184): Vertex AI (Google Cloud credits) when VERTEX_API_KEY is set, else AI Studio.
    # The choice itself lives in agents/gateway.py; these are read here only to check the setup at start.
    STUDIO_API_KEY: str = os.getenv("STUDIO_API_KEY", "")   # not GEMINI_API_KEY: see agents/gateway.py
    VERTEX_API_KEY: str = os.getenv("VERTEX_API_KEY", "")
    VERTEX_PROJECT: str = os.getenv("VERTEX_PROJECT", "")   # informational: the key already names it
    CLARIFICATION_MODEL: str = os.getenv("CLARIFICATION_MODEL", "gemini-3.8-flash")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "gemini-3.1-flash-lite")

    # Paused runs (LangGraph checkpoints, D-123). SQLite file at the FORGE-1 root, gitignored by *.db
    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", str(ROOT_DIR / "forge_checkpoints.db"))

    # PostgreSQL (Supabase). App database and a separate one for the integration tests (D-172).
    # Both may be pooler URLs; the engine disables prepared-statement caching for that (backend/db/session.py).
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "")
    # How long project creation waits for the per-user lock before answering 503 (D-174)
    DB_LOCK_TIMEOUT_MS: int = int(os.getenv("DB_LOCK_TIMEOUT_MS", "3000"))

    # Limits against cost and abuse (D-189 - D-194). Every value can be changed in .env.
    LIMIT_REQUESTS_PER_USER_DAY: int = int(os.getenv("LIMIT_REQUESTS_PER_USER_DAY", "20"))
    LIMIT_REQUESTS_PER_DAY: int = int(os.getenv("LIMIT_REQUESTS_PER_DAY", "300"))
    LIMIT_SIGNUPS_PER_IP_HOUR: int = int(os.getenv("LIMIT_SIGNUPS_PER_IP_HOUR", "5"))
    LIMIT_SIGNUPS_PER_IP_DAY: int = int(os.getenv("LIMIT_SIGNUPS_PER_IP_DAY", "20"))
    LIMIT_SIGNUPS_PER_DAY: int = int(os.getenv("LIMIT_SIGNUPS_PER_DAY", "200"))
    LIMIT_FORGOT_PER_IP_HOUR: int = int(os.getenv("LIMIT_FORGOT_PER_IP_HOUR", "10"))
    LIMIT_EMAILS_PER_DAY: int = int(os.getenv("LIMIT_EMAILS_PER_DAY", "400"))
    LIMIT_LOGIN_FAILS_PER_IP_ACCOUNT: int = int(os.getenv("LIMIT_LOGIN_FAILS_PER_IP_ACCOUNT", "5"))      # per 15 min
    LIMIT_LOGIN_FAILS_PER_ACCOUNT_HOUR: int = int(os.getenv("LIMIT_LOGIN_FAILS_PER_ACCOUNT_HOUR", "30"))
    LIMIT_LOGIN_FAILS_PER_IP: int = int(os.getenv("LIMIT_LOGIN_FAILS_PER_IP", "30"))                      # per 10 min
    LIMIT_WEBSITE_READS_PER_USER_DAY: int = int(os.getenv("LIMIT_WEBSITE_READS_PER_USER_DAY", "10"))
    LIMIT_IMAGE_READS_PER_USER_HOUR: int = int(os.getenv("LIMIT_IMAGE_READS_PER_USER_HOUR", "30"))
    MAX_IMAGE_UPLOAD_BYTES: int = int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(2_621_440)))   # 2.5 MB incl. form overhead
    MAX_JSON_BODY_BYTES: int = int(os.getenv("MAX_JSON_BODY_BYTES", "65536"))

    # Sign-in (D-176 - D-178). Secrets live only in .env; tokens are refused if a secret is missing or short.
    JWT_ACCESS_SECRET: str = os.getenv("JWT_ACCESS_SECRET", "")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "")
    JWT_ISSUER: str = "forge-api"
    JWT_AUDIENCE: str = "forge-app"
    ACCESS_TOKEN_MINUTES: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    REFRESH_TOKEN_DAYS: int = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))
    # The refresh cookie is sent over HTTPS only outside development
    COOKIE_SECURE: bool = os.getenv("ENVIRONMENT", "development").lower() != "development"

    # Email for verification and password reset (D-187). Without SMTP_HOST, emails are only logged.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").replace(" ", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "").strip()
    # The site the links in emails open (the Next.js frontend)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

    # Server config
    PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # CORS settings: comma-separated list in CORS_ORIGIN
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGIN", "http://localhost:3000").split(",")
        if origin.strip()
    ]


settings = Settings()

if not (settings.VERTEX_API_KEY or settings.STUDIO_API_KEY):
    raise ValueError("No model key: set VERTEX_API_KEY (Vertex AI) or STUDIO_API_KEY (AI Studio) in FORGE-1/.env.")
