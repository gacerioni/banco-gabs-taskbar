"""
API Endpoints
All FastAPI endpoint routers
"""

from .health import router as health_router
from .seed import router as seed_router
from .search import router as search_router
from .autocomplete import router as autocomplete_router
from .feedback import router as feedback_router

__all__ = [
    'health_router',
    'seed_router',
    'search_router',
    'autocomplete_router',
    'feedback_router',
]
