import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Set up paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Supply-Chain Financing Marketplace"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "94e7732a392b4fa3e46c7bc3793df6033bb27e025b392cd97dfebf65e2beec9a"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 180

    # Database
    DATABASE_URL: str = "sqlite:///./supply_chain.db"

    # Configurable Risk Thresholds
    RISK_THRESHOLD_LOW: int = 30
    RISK_THRESHOLD_MEDIUM: int = 60

    # Upload Directory
    UPLOAD_DIR: str = "uploads"

    # Model Config
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure uploads directory exists
UPLOAD_PATH = BASE_DIR / settings.UPLOAD_DIR
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

# Ensure ML models directory exists
ML_MODELS_PATH = BASE_DIR / "ml_models"
ML_MODELS_PATH.mkdir(parents=True, exist_ok=True)
