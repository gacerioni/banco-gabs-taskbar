"""
Redis Client Module
Centralized Redis connection and client management
"""

import redis
from typing import Optional


# ============================================================================
# GLOBAL STATE
# ============================================================================

_redis_client: Optional[redis.Redis] = None


# ============================================================================
# REDIS CLIENT
# ============================================================================

def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client (singleton pattern).

    Uses REDIS_URL from config.

    Returns:
        redis.Redis instance
    """
    global _redis_client

    if _redis_client is None:
        from ..core.config import config

        redis_url = config.REDIS_URL
        print(f"🔗 Connecting to Redis: {redis_url[:20]}...")
        
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Test connection
        try:
            _redis_client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    return _redis_client


def close_redis_client():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        print("🔌 Redis connection closed")


# ============================================================================
# REDIS INFO
# ============================================================================

def get_redis_info() -> dict:
    """Get Redis server information"""
    client = get_redis_client()
    return {
        "connected": True,
        "db_size": client.dbsize(),
        "info": client.info("server")
    }

