"""
Search Module
Hybrid search (text + vector) functionality
"""

from .vectorizer import get_search_vectorizer, embed_text, embed_texts
from .hybrid_search import hybrid_search
from .autocomplete import setup_autocomplete, autocomplete_search

__all__ = [
    'get_search_vectorizer',
    'embed_text',
    'embed_texts',
    'hybrid_search',
    'setup_autocomplete',
    'autocomplete_search',
]
