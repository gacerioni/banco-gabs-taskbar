"""
Vectorizer Module
Manages embedding models for search

Uses Qwen3 (gte-Qwen2-1.5B-instruct) for high-quality embeddings
"""

from typing import Optional, List
import numpy as np
from redisvl.utils.vectorize import HFTextVectorizer


# ============================================================================
# GLOBAL STATE
# ============================================================================

_search_vectorizer: Optional[HFTextVectorizer] = None


# ============================================================================
# SEARCH VECTORIZER
# ============================================================================

def get_search_vectorizer() -> HFTextVectorizer:
    """
    Get or create vectorizer for search.
    Uses model from config (configurable via .env).

    This is the SAME model used for routing (memory efficient!)

    Returns:
        HFTextVectorizer instance
    """
    global _search_vectorizer

    if _search_vectorizer is None:
        from ..core.config import config

        print(f"🤖 Loading search vectorizer: {config.EMBEDDING_MODEL}")
        _search_vectorizer = HFTextVectorizer(
            model=config.EMBEDDING_MODEL
            # Note: dims is auto-detected from the model
        )
        print(f"✅ Search vectorizer loaded ({config.EMBEDDING_DIM} dims)")

    return _search_vectorizer


def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        List of floats (dimension from config)
    """
    vectorizer = get_search_vectorizer()
    return vectorizer.embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (batched).
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embeddings
    """
    vectorizer = get_search_vectorizer()
    return vectorizer.embed_many(texts)

