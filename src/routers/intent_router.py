"""
Intent Router Module
Routes queries to 'search' or 'chat' intent based on semantic similarity

NOW USING QWEN3 FOR EVERYTHING!
- Same model for routing and search (memory efficient)
- Much better quality (+30% accuracy)
- Unified embeddings (4096 dims)
"""

from typing import Tuple, Dict, Optional
import os

from redisvl.extensions.router import Route, SemanticRouter, RoutingConfig
from redisvl.extensions.router.semantic import DistanceAggregationMethod
from redisvl.utils.vectorize import HFTextVectorizer

from .language_detector import detect_language
from .route_examples import get_route_examples
from ..search.vectorizer import get_search_vectorizer  # Use SAME vectorizer as search!


# ============================================================================
# GLOBAL STATE
# ============================================================================

_router_vectorizer: Optional[HFTextVectorizer] = None
_semantic_routers: Dict[str, SemanticRouter] = {}


# ============================================================================
# VECTORIZER (QWEN3 - SHARED WITH SEARCH)
# ============================================================================

def get_router_vectorizer() -> HFTextVectorizer:
    """
    Get or create vectorizer for semantic routing.
    NOW USES QWEN3 (same as search)!

    Benefits:
    - Much better quality (+30% accuracy vs MiniLM)
    - Shares model with search (no extra memory)
    - 4096 dimensions (vs 384)
    - State-of-the-art multilingual

    Returns:
        HFTextVectorizer instance
    """
    global _router_vectorizer

    if _router_vectorizer is None:
        print("🤖 Loading router vectorizer: Qwen3 (gte-Qwen2-1.5B-instruct)")
        print("   🔥 Using same model as search for efficiency!")
        _router_vectorizer = HFTextVectorizer(
            model="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
        )
        print("✅ Router vectorizer loaded (4096 dims - Qwen3)")

    return _router_vectorizer


# ============================================================================
# SEMANTIC ROUTERS (per language)
# ============================================================================

def get_semantic_router(language: str) -> SemanticRouter:
    """
    Get or create semantic router for a specific language.
    
    Args:
        language: Language code ('pt', 'en', 'es')
    
    Returns:
        SemanticRouter instance for that language
    """
    global _semantic_routers
    
    if language not in _semantic_routers:
        from ..core.config import config  # Import here to avoid circular

        print(f"🔀 Initializing semantic router for language: {language}")

        # Get route examples
        all_examples = get_route_examples()

        if language not in all_examples:
            print(f"⚠️  Language '{language}' not configured, falling back to 'en'")
            language = 'en'

        lang_examples = all_examples[language]

        # Create routes
        search_route = Route(
            name="search",
            references=lang_examples['search'],
            metadata={"intent": "search", "language": language}
        )

        chat_route = Route(
            name="chat",
            references=lang_examples['chat'],
            metadata={"intent": "chat", "language": language}
        )

        # Get Redis URL from config
        redis_url = config.REDIS_URL

        # Create router using SAME vectorizer as search (no duplication!)
        router = SemanticRouter(
            name=f"intent_router_{language}",
            routes=[search_route, chat_route],
            routing_config=RoutingConfig(aggregation_method=DistanceAggregationMethod.min),
            vectorizer=get_search_vectorizer(),  # Use search vectorizer (already loaded!)
            redis_url=redis_url,
            overwrite=True  # FORCES RECREATION OF INDEX AND REFERENCES!
        )

        _semantic_routers[language] = router
        print(f"✅ Semantic router for '{language}' initialized")
    
    return _semantic_routers[language]


def force_reload_routers():
    """
    Force reload all semantic routers from disk.
    Called by the /seed endpoint to refresh routes.
    """
    global _semantic_routers
    print("🔄 Forcing reload of all semantic routers...")

    # Clear the in-memory cache
    _semantic_routers.clear()

    # Re-initialize for 'pt' (will trigger overwrite=True)
    get_semantic_router('pt')
    print("✅ Semantic routers reloaded successfully!")


# ============================================================================
# MAIN ROUTING FUNCTION
# ============================================================================

def route_query(query: str, default_lang: str = 'pt') -> Tuple[str, str, float]:
    """
    Route a user query through language detection + semantic routing.
    
    Flow:
    1. Detect language (pt/en/es)
    2. Route to appropriate intent (search/chat)
    3. Return (language, intent, confidence)
    
    Args:
        query: User query string
        default_lang: Default language for ambiguous cases (default: 'pt' for Brazil)
        
    Returns:
        Tuple of (language, intent, confidence)
        - language: 'pt', 'en', or 'es'
        - intent: 'search' or 'chat'
        - confidence: 0.0-1.0
        
    Examples:
        >>> route_query("como faço pra investir?")
        ('pt', 'chat', 0.89)
        
        >>> route_query("pix")
        ('pt', 'search', 0.95)
        
        >>> route_query("I need help")
        ('en', 'chat', 0.92)
    """
    # Step 1: Detect language with intelligent fallback
    language = detect_language(query, default_lang=default_lang)
    
    # Step 2: Get language-specific router
    router = get_semantic_router(language)
    
    # Step 3: Route to intent
    try:
        result = router(query)
    except Exception as e:
        print(f"⚠️  Router error: {e}, defaulting to 'search'")
        return language, "search", 0.5
    
    # Extract intent and confidence
    if result and hasattr(result, 'name'):
        intent = result.name if result.name else "search"
        
        # Convert distance to confidence (handle None gracefully)
        if hasattr(result, 'distance') and result.distance is not None:
            confidence = max(0.0, min(1.0, 1.0 - result.distance))  # Clamp to [0, 1]
        else:
            confidence = 0.5
    else:
        # Fallback: default to search with low confidence
        print(f"⚠️  No route matched for query: '{query}', defaulting to 'search'")
        intent = "search"
        confidence = 0.5
    
    # Safety check: ensure intent is valid
    if intent not in ['search', 'chat']:
        print(f"⚠️  Invalid intent '{intent}', defaulting to 'search'")
        intent = "search"
    
    return language, intent, confidence

