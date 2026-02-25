"""
Configuration module for Banco Inter Taskbar Search
Reads from environment variables with sensible defaults
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # ============================================================================
    # REDIS CONFIGURATION
    # ============================================================================
    
    # Redis connection URL (supports authentication)
    # Format: redis://[username:password@]host:port[/db]
    # Example: redis://default:mypassword@redis-12345.cloud.redislabs.com:12345
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    
    # ============================================================================
    # EMBEDDING CONFIGURATION
    # ============================================================================
    
    # Embedding model and dimensions
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
    
    # ============================================================================
    # SEARCH CONFIGURATION
    # ============================================================================
    
    # Default search parameters
    DEFAULT_LIMIT: int = int(os.getenv("DEFAULT_LIMIT", "5"))
    POPULARITY_WEIGHT: float = float(os.getenv("POPULARITY_WEIGHT", "0.3"))
    
    # Semantic router thresholds (currently disabled, but preserved for future use)
    SEMANTIC_ROUTER_DISTANCE_THRESHOLD: float = float(
        os.getenv("SEMANTIC_ROUTER_DISTANCE_THRESHOLD", "0.55")
    )
    
    # ============================================================================
    # APPLICATION CONFIGURATION
    # ============================================================================
    
    # FastAPI settings
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    
    # CORS settings
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration"""
        if not cls.REDIS_URL:
            raise ValueError("REDIS_URL must be set in environment or .env file")
        
        if not cls.REDIS_URL.startswith(("redis://", "rediss://")):
            raise ValueError(
                "REDIS_URL must start with 'redis://' or 'rediss://' (for SSL)"
            )
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL with validation"""
        cls.validate()
        return cls.REDIS_URL
    
    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (for debugging)"""
        print("=" * 60)
        print("🏦 Banco Inter Taskbar Search - Configuration")
        print("=" * 60)
        print(f"Redis URL: {cls._mask_password(cls.REDIS_URL)}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL}")
        print(f"Embedding Dimensions: {cls.EMBEDDING_DIM}")
        print(f"Default Limit: {cls.DEFAULT_LIMIT}")
        print(f"Popularity Weight: {cls.POPULARITY_WEIGHT}")
        print(f"App Host: {cls.APP_HOST}")
        print(f"App Port: {cls.APP_PORT}")
        print(f"Debug Mode: {cls.DEBUG}")
        print("=" * 60)
    
    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in Redis URL for safe logging"""
        if "@" in url and ":" in url:
            # Format: redis://user:password@host:port
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0]
                if ":" in auth_part:
                    protocol_user = auth_part.rsplit(":", 1)[0]
                    return f"{protocol_user}:****@{parts[1]}"
        return url


# Create singleton instance
config = Config()

