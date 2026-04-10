"""
API Module
FastAPI application and endpoints
"""

from .endpoints import (
    health_router,
    seed_router,
    search_router,
    autocomplete_router,
    feedback_router
)

__all__ = [
    'health_router',
    'seed_router',
    'search_router',
    'autocomplete_router',
    'feedback_router'
]
