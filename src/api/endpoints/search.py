"""
Search Endpoints
Unified search with semantic routing
"""

from fastapi import APIRouter, Query
from typing import Dict, Any, List
import time
import uuid

from ...data import get_redis_client
from ...search.hybrid_search import hybrid_search
from ...routers import route_query
from ...chat import handle_chat_query
from ...core.models import UnifiedSearchResponse


router = APIRouter()


@router.get("/search")
async def legacy_search(
    q: str = Query(..., description="Search query"),
    lang: str = Query("pt", description="Language code (pt, en, es)"),
    country: str = Query("BR", description="Country code"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
) -> Dict[str, Any]:
    """
    Legacy search endpoint (backward compatible).
    Always performs hybrid search.
    """
    redis_client = get_redis_client()
    start = time.time()

    results, redis_time_ms = hybrid_search(
        redis_client=redis_client,
        query=q,
        lang=lang,
        country=country,
        limit=limit,
        fts_weight=0.7,
        vss_weight=0.3,
        rrf_k=10
    )

    latency = (time.time() - start) * 1000

    return {
        "tracking_id": str(uuid.uuid4()),
        "latency_ms": round(latency, 2),
        "redis_time_ms": redis_time_ms,
        "query": q,
        "total": len(results),
        "results": results
    }


@router.get("/api/search")
async def unified_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    use_openai: bool = Query(False, description="Use OpenAI for chat (requires API key)"),
    fts_weight: float = Query(0.7, ge=0.0, le=1.0, description="Weight for text search"),
    vss_weight: float = Query(0.3, ge=0.0, le=1.0, description="Weight for semantic search"),
    rrf_k: int = Query(10, ge=1, le=100, description="RRF constant K")
) -> Dict[str, Any]:
    """
    Unified search with semantic routing.
    
    Routes to:
    - SEARCH intent → Hybrid search (Redis 8.6 native)
    - CHAT intent → Conversational AI (mock or OpenAI)
    """
    redis_client = get_redis_client()
    start = time.time()
    tracking_id = str(uuid.uuid4())
    
    # Route query (language detection + intent routing)
    language, intent, confidence = route_query(q)
    
    print(f"🔀 Routing: '{q}' → {language.upper()} / {intent.upper()} ({confidence:.2%})")
    
    if intent == "chat":
        # Chat intent - conversational AI
        chat_result = handle_chat_query(
            query=q,
            language=language,
            use_openai=use_openai
        )
        
        latency = (time.time() - start) * 1000
        
        return {
            "tracking_id": tracking_id,
            "latency_ms": round(latency, 2),
            "query": q,
            "language": language,
            "intent": "chat",
            "confidence": confidence,
            "chat_response": chat_result["response"],
            "chat_provider": chat_result["provider"],
            "chat_model": chat_result.get("model", "mock")
        }
    
    else:
        # Search intent - hybrid search
        results, redis_time_ms = hybrid_search(
            redis_client=redis_client,
            query=q,
            lang=language,
            country="BR",  # TODO: detect from language or config
            limit=limit,
            fts_weight=fts_weight,
            vss_weight=vss_weight,
            rrf_k=rrf_k
        )

        latency = (time.time() - start) * 1000

        return {
            "tracking_id": tracking_id,
            "latency_ms": round(latency, 2),
            "redis_time_ms": redis_time_ms,
            "query": q,
            "language": language,
            "intent": "search",
            "confidence": confidence,
            "total": len(results),
            "results": results
        }

