"""
Search Module
Hybrid search (text + vector) functionality
"""

from .vectorizer import get_search_vectorizer, embed_text, embed_texts
from .hybrid_search import hybrid_search, build_fts_prefix_query
from .autocomplete import setup_autocomplete, autocomplete_search
from .spellcheck import spellcheck_query, get_corrected_query
from .query_cache import get_cached_results, cache_results, invalidate_search_cache

__all__ = [
    'get_search_vectorizer',
    'embed_text',
    'embed_texts',
    'hybrid_search',
    'build_fts_prefix_query',
    'setup_autocomplete',
    'autocomplete_search',
    'spellcheck_query',
    'get_corrected_query',
    'get_cached_results',
    'cache_results',
    'invalidate_search_cache',
]
