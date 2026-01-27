"""
Configuration management for the backend application.
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # API Configuration
    API_HOST: str = os.getenv("HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Google Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    # Paths
    REPO_CACHE_DIR: str = os.getenv("REPO_CACHE_DIR", "./repos")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required settings are present.
        
        Returns:
            True if all required settings are present
        """
        # Google Gemini API key is optional (some features won't work without it)
        return True

    @classmethod
    def get_cors_origins(cls) -> list:
        """Get CORS origins, including any from environment."""
        origins = cls.CORS_ORIGINS.copy()
        
        # Add any additional origins from environment
        additional_origins = os.getenv("CORS_ORIGINS", "")
        if additional_origins:
            origins.extend([origin.strip() for origin in additional_origins.split(",")])
        
        return origins


# Global settings instance
settings = Settings()
