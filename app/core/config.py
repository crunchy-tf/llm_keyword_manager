# app/core/config.py
import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import json
import logging

# Load .env file variables into environment first
load_dotenv()

class Settings(BaseSettings):
    """ Application settings loaded from environment variables and .env file. """
    PROJECT_NAME: str = Field("Minbar Keyword Manager", description="Name of the project.")
    API_V1_STR: str = Field("/api/v1", description="API version prefix.")
    LOG_LEVEL: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).")

    # --- Database Settings ---
    MONGO_URI: str = Field(..., description="MongoDB connection string.")
    MONGO_DB_NAME: str = Field("minbar_keywords", description="Name of the MongoDB database.")
    MONGO_COLLECTION_CONCEPTS: str = Field("concepts", description="Name of the MongoDB collection for concepts.")

    # --- LLM Settings (Google Gemini) ---
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY", description="API key for Google Gemini.")
    GEMINI_LLM_MODEL: str = Field("gemini-1.5-flash-latest", env="GEMINI_LLM_MODEL", description="Gemini model ID to use.")
    LLM_TEMPERATURE: float = Field(0.3, ge=0.0, le=1.0, description="Default LLM temperature.")
    LLM_MAX_TOKENS_GENERATION: int = Field(150, gt=0, description="Default max output tokens for concept generation.")
    LLM_MAX_TOKENS_TRANSLATION: int = Field(50, gt=0, description="Default max output tokens for translation.")
    # --- End LLM Settings ---

    # --- Service Logic Parameters ---
    LOW_YIELD_THRESHOLD: float = Field(0.3, ge=0.0, le=1.0, description="Relevance feedback below this threshold is negative.")
    KEYWORD_DEACTIVATION_THRESHOLD: float = Field(0.2, ge=0.0, le=1.0, description="Concept score below this deactivates it.")
    SCORE_DECAY_FACTOR: float = Field(0.95, gt=0.0, lt=1.0, description="Multiplier for score on negative feedback.")
    CONFIDENCE_DECAY_ENABLED: bool = Field(True, description="Enable/disable time-based confidence decay.")
    CONFIDENCE_DECAY_PERIOD_DAYS: int = Field(14, gt=0, description="Days without positive feedback before decay.")
    CONFIDENCE_TIME_DECAY_FACTOR: float = Field(0.98, gt=0.0, lt=1.0, description="Multiplier for score during time decay.")

    # --- Scheduler Configuration ---
    SCHEDULER_INTERVAL_MINUTES: int = Field(60, gt=0, description="Interval (minutes) for background tasks.")

    # --- CORS Configuration ---
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field([], description="List of allowed CORS origins.")

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[AnyHttpUrl]:
        """ Parses CORS origins from env var (JSON list or comma-separated string). """
        if isinstance(v, list): return [AnyHttpUrl(str(origin)) for origin in v] # Ensure elements are URL types
        if isinstance(v, str):
            if not v: return [] # Handle empty string case
            if v.startswith("[") and v.endswith("]"):
                try: origins = json.loads(v); return [AnyHttpUrl(str(origin)) for origin in origins]
                except json.JSONDecodeError: raise ValueError(f"Invalid JSON: {v}")
            else: return [AnyHttpUrl(origin.strip()) for origin in v.split(",") if origin.strip()]
        raise ValueError(f"Invalid type for BACKEND_CORS_ORIGINS: {type(v)}")

    model_config = ConfigDict(
        case_sensitive=True, env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )

# Create a single settings instance
settings = Settings()

# Define supported languages constant
SUPPORTED_LANGUAGES = ["en", "fr", "ar"]

# Configure logging based on settings
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')