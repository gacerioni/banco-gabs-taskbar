"""
Health Endpoint
System health check and Redis status
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ...data import get_redis_client, get_redis_info
from ...core.models import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns server status and Redis connection info.
    """
    try:
        redis_info = get_redis_info()
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "redis_connected": redis_info["connected"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "2.0.0",
            "redis_connected": False
        }

