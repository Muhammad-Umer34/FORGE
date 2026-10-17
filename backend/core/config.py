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

    # API Keys & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gemini-3.8-flash")
    CLARIFICATION_MODEL: str = os.getenv("CLARIFICATION_MODEL", "gemini-3.8-flash")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "gemini-3.1-flash-lite")
    MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.7"))

    # Paused runs (LangGraph checkpoints, D-123). SQLite file at the FORGE-1 root, gitignored by *.db
    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", str(ROOT_DIR / "forge_checkpoints.db"))

    # PostgreSQL (Supabase). App database and a separate one for the integration tests (D-172).
    # Both may be pooler URLs; the engine disables prepared-statement caching for that (backend/db/session.py).
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "")
    # How long project creation waits for the per-user lock before answering 503 (D-174)
    DB_LOCK_TIMEOUT_MS: int = int(os.getenv("DB_LOCK_TIMEOUT_MS", "3000"))

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

if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing! Please configure it in the FORGE-1/.env file.")
