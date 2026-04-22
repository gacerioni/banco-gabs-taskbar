"""
Search Endpoints
Unified search with semantic routing, latency breakdown, query caching
"""

from fastapi import APIRouter, Query
from typing import Dict, Any
import time
import uuid

from ...data import get_redis_client
from ...search.hybrid_search import hybrid_search
from ...search.query_cache import get_cached_results, cache_results
from ...routers import route_query
from ...chat import handle_chat_query
from ...core.config import config


router = APIRouter()


def _routing_meta(_language: str, intent: str, confidence: float) -> Dict[str, Any]:
    """Flags when semantic intent confidence is below threshold (UI can nudge the user)."""
    low = confidence < config.INTENT_CONFIDENCE_LOW
    meta: Dict[str, Any] = {"routing_low_confidence": low}
    if not low:
        return meta
    # English copy: demo UI is EN-first; conversation language may still be pt/en from the model.
    meta["routing_hint"] = (
        "Intent routing confidence is low. If this feels wrong, try short product-style keywords for search, "
        "or open the Concierge 💬 panel for chat (Portuguese or English works in the demo data)."
    )
    meta["routing_intent_guess"] = intent
    return meta


@router.get("/search")
async def legacy_search(
    q: str = Query(..., description="Search query"),
    lang: str = Query("pt", description="Language code (pt, en, es)"),
    country: str = Query("BR", description="Country code"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
) -> Dict[str, Any]:
    """
    Legacy search endpoint (backward compatible).
    Always performs hybrid search with caching and latency breakdown.
    """
    redis_client = get_redis_client()
    start = time.time()

    # Check cache first
    cached = get_cached_results(redis_client, q, lang, limit, 0.7, 0.3, 10)
    if cached:
        results, metadata = cached
        latency = (time.time() - start) * 1000
        return {
            "tracking_id": str(uuid.uuid4()),
            "latency_ms": round(latency, 2),
            "redis_time_ms": metadata.get("total_redis_ms", 0),
            "breakdown": metadata,
            "query": q,
            "total": len(results),
            "results": results
        }

    results, metadata = hybrid_search(
        redis_client=redis_client,
        query=q,
        lang=lang,
        country=country,
        limit=limit,
        fts_weight=0.7,
        vss_weight=0.3,
        rrf_k=10
    )

    # Cache results
    cache_results(redis_client, q, lang, limit, 0.7, 0.3, 10, results, metadata)

    latency = (time.time() - start) * 1000

    return {
        "tracking_id": str(uuid.uuid4()),
        "latency_ms": round(latency, 2),
        "redis_time_ms": metadata.get("total_redis_ms", 0),
        "breakdown": metadata,
        "query": q,
        "total": len(results),
        "results": results
    }


@router.get("/api/search")
async def unified_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    use_openai: bool = Query(False, description="Use OpenAI concierge for chat (requires API key)"),
    session_id: str = Query("", description="Stable session id for concierge cart (persist client-side)"),
    fts_weight: float = Query(0.7, ge=0.0, le=1.0, description="Weight for text search"),
    vss_weight: float = Query(0.3, ge=0.0, le=1.0, description="Weight for semantic search"),
    rrf_k: int = Query(10, ge=1, le=100, description="RRF constant K")
) -> Dict[str, Any]:
    """
    Unified search with semantic routing.
    
    Routes to:
    - SEARCH intent → Hybrid search (Redis 8.6 native) with caching
    - CHAT intent → Conversational AI (mock or OpenAI)
    
    Response includes latency breakdown and match explanations.
    """
    redis_client = get_redis_client()
    start = time.time()
    tracking_id = str(uuid.uuid4())
    
    # Route query (language detection + intent routing)
    language, intent, confidence = route_query(q)
    
    print(f"Routing: '{q}' -> {language.upper()} / {intent.upper()} ({confidence:.2%})")
    
    if intent == "chat":
        # Chat intent — concierge (Redis SKUs + cart) or mock
        chat_result = handle_chat_query(
            query=q,
            language=language,
            use_openai=use_openai,
            redis_client=redis_client,
            session_id=session_id.strip() or None,
            include_tool_trace=config.DEBUG,
        )

        latency = (time.time() - start) * 1000

        payload: Dict[str, Any] = {
            "tracking_id": tracking_id,
            "latency_ms": round(latency, 2),
            "query": q,
            "language": language,
            "intent": "chat",
            "confidence": confidence,
            "chat_response": chat_result["response"],
            "chat_provider": chat_result["provider"],
            "chat_model": chat_result.get("model", "mock"),
            "session_id": chat_result.get("session_id"),
            "cart": chat_result.get("cart"),
        }
        if chat_result.get("tool_trace") is not None:
            payload["tool_trace"] = chat_result["tool_trace"]
        for _k, _v in chat_result.items():
            if _k.startswith("guard_"):
                payload[_k] = _v
        payload.update(_routing_meta(language, intent, confidence))
        return payload
    
    else:
        # Search intent - check cache first
        cached = get_cached_results(redis_client, q, language, limit, fts_weight, vss_weight, rrf_k)
        if cached:
            results, metadata = cached
            latency = (time.time() - start) * 1000
            response = {
                "tracking_id": tracking_id,
                "latency_ms": round(latency, 2),
                "redis_time_ms": metadata.get("total_redis_ms", 0),
                "breakdown": metadata,
                "query": q,
                "language": language,
                "intent": "search",
                "confidence": confidence,
                "total": len(results),
                "results": results
            }
            if metadata.get("corrected_query"):
                response["did_you_mean"] = metadata["corrected_query"]
                response["spellcheck_suggestions"] = metadata["spellcheck_suggestions"]
            response.update(_routing_meta(language, intent, confidence))
            return response

        # Search intent - hybrid search
        results, metadata = hybrid_search(
            redis_client=redis_client,
            query=q,
            lang=language,
            country="BR",
            limit=limit,
            fts_weight=fts_weight,
            vss_weight=vss_weight,
            rrf_k=rrf_k
        )

        # Cache results
        cache_results(redis_client, q, language, limit, fts_weight, vss_weight, rrf_k, results, metadata)

        latency = (time.time() - start) * 1000

        response = {
            "tracking_id": tracking_id,
            "latency_ms": round(latency, 2),
            "redis_time_ms": metadata.get("total_redis_ms", 0),
            "breakdown": metadata,
            "query": q,
            "language": language,
            "intent": "search",
            "confidence": confidence,
            "total": len(results),
            "results": results
        }

        # Include spellcheck info if available
        if metadata.get("corrected_query"):
            response["did_you_mean"] = metadata["corrected_query"]
            response["spellcheck_suggestions"] = metadata["spellcheck_suggestions"]

        response.update(_routing_meta(language, intent, confidence))
        return response

