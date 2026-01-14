"""
Configuration management using Pydantic Settings
Loads from environment variables and .env file
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # App Settings
    app_name: str = Field(default="AI Crop Doctor API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database
    database_url: str = Field(
        default="sqlite:///./database/crop_doctor.db",
        alias="DATABASE_URL"
    )

    # AI Model
    model_name: str = Field(default="Qwen/Qwen2.5-Omni-7B", alias="MODEL_NAME")
    model_device: str = Field(default="auto", alias="MODEL_DEVICE")  # "auto", "cuda:0", "cuda:1", "cuda:2", etc.
    use_4bit_quantization: bool = Field(default=True, alias="USE_4BIT_QUANTIZATION")
    enable_audio_output: bool = Field(default=False, alias="ENABLE_AUDIO_OUTPUT")

    # File Upload
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=10, alias="MAX_FILE_SIZE_MB")

    # JWT Auth
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        alias="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Epidemic Detection
    dbscan_eps: float = Field(default=0.05, alias="DBSCAN_EPS")
    dbscan_min_samples: int = Field(default=5, alias="DBSCAN_MIN_SAMPLES")
    epidemic_lookback_days: int = Field(default=7, alias="EPIDEMIC_LOOKBACK_DAYS")

    # Expert Review
    auto_review_threshold: float = Field(default=0.7, alias="AUTO_REVIEW_THRESHOLD")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
