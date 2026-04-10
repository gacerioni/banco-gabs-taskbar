"""
Routers Module
Language detection + Intent routing (search vs chat)
"""

from .language_detector import detect_language, get_language_detector
from .intent_router import route_query, get_semantic_router
from .route_examples import get_route_examples

__all__ = [
    'detect_language',
    'get_language_detector',
    'route_query',
    'get_semantic_router',
    'get_route_examples',
]
