"""Configuration settings for VnStock Screener backend."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # ===========================================
    # Database Configuration
    # ===========================================
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", 
        str(Path(__file__).parent / "data" / "vnstock_data.db")
    )
    
    # ===========================================
    # VnStock Rate Limiting (CRITICAL for 24/7)
    # ===========================================
    # Conservative rate limit to avoid API blocks
    VNSTOCK_RATE_LIMIT: int = int(os.getenv("VNSTOCK_RATE_LIMIT", "6"))  # requests per minute
    
    # Token bucket settings for smooth rate limiting
    TOKEN_BUCKET_CAPACITY: int = int(os.getenv("TOKEN_BUCKET_CAPACITY", "6"))
    TOKEN_REFILL_RATE: float = float(os.getenv("TOKEN_REFILL_RATE", "0.1"))  # tokens per second
    
    # ===========================================
    # Exponential Backoff Settings
    # ===========================================
    BACKOFF_BASE_DELAY: float = float(os.getenv("BACKOFF_BASE_DELAY", "1.0"))  # seconds
    BACKOFF_MAX_DELAY: float = float(os.getenv("BACKOFF_MAX_DELAY", "300.0"))  # 5 minutes max
    BACKOFF_MULTIPLIER: float = float(os.getenv("BACKOFF_MULTIPLIER", "2.0"))
    
    # ===========================================
    # Circuit Breaker Settings
    # ===========================================
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "300"))  # 5 minutes
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "1"))
    
    # ===========================================
    # Update Scheduling
    # ===========================================
    # After market close (Vietnam market closes at 15:00, update at 18:00)
    DAILY_UPDATE_TIME: str = os.getenv("DAILY_UPDATE_TIME", "18:00")
    WEEKLY_UPDATE_DAY: str = os.getenv("WEEKLY_UPDATE_DAY", "saturday")
    WEEKLY_UPDATE_TIME: str = os.getenv("WEEKLY_UPDATE_TIME", "20:00")
    
    # Market hours (Vietnam: 9:00-11:30, 13:00-15:00)
    MARKET_OPEN_HOUR: int = int(os.getenv("MARKET_OPEN_HOUR", "9"))
    MARKET_CLOSE_HOUR: int = int(os.getenv("MARKET_CLOSE_HOUR", "15"))
    
    # ===========================================
    # Data Collection Settings
    # ===========================================
    DEFAULT_VNSTOCK_SOURCE: str = os.getenv("DEFAULT_VNSTOCK_SOURCE", "TCBS")
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # Price history settings
    PRICE_HISTORY_DAYS: int = int(os.getenv("PRICE_HISTORY_DAYS", "365"))
    
    # Proxy Settings (vnstock 3.3.1+)
    # Enable automatic proxy for avoiding IP blocks
    ENABLE_VNSTOCK_PROXY: bool = os.getenv("ENABLE_VNSTOCK_PROXY", "false").lower() == "true"
    
    # ===========================================
    # Logging Configuration
    # ===========================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/vnstock_updater.log")
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "7 days")
    
    # ===========================================
    # Health Monitoring
    # ===========================================
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
    STALE_DATA_THRESHOLD_HOURS: int = int(os.getenv("STALE_DATA_THRESHOLD_HOURS", "24"))
    
    # ===========================================
    # API Server Settings
    # ===========================================
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
