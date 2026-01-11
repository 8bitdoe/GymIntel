"""
GymIntel Configuration
Load environment variables and define app settings.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "GymIntel"
    DEBUG: bool = True

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "gymintel"

    # TwelveLabs
    TWELVELABS_API_KEY: str = ""
    TWELVELABS_INDEX_NAME: str = "gymintel-workouts"

    # Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-native-audio-dialog"
    GEMINI_ANALYSIS_MODEL: str = "gemini-2.0-flash"

    # Snowflake (for social/benchmarking features)
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_USER: str = ""
    SNOWFLAKE_PASSWORD: str = ""
    SNOWFLAKE_WAREHOUSE: str = "GYMINTEL_WH"
    SNOWFLAKE_DATABASE: str = "GYMINTEL_DB"
    SNOWFLAKE_SCHEMA: str = "PUBLIC"

    # Optional: Deepgram + ElevenLabs (for later)
    DEEPGRAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Quick access
settings = get_settings()

# ============================================================
# Example .env file (create this in your project root):
# ============================================================
"""
# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=gymintel

# TwelveLabs
TWELVELABS_API_KEY=your_twelvelabs_api_key_here

# Google Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password

# Optional (for later)
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
"""