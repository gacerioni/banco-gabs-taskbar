"""
Query Cache Module - Redis-based search result caching
Demonstrates Redis as a high-performance cache layer for search results.

First search = full pipeline (~80ms), second identical search = cache hit (~2ms)
"""

import json
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple

import redis

from ..core.config import config


def _build_cache_key(query: str, lang: str, limit: int, fts_weight: float, vss_weight: float, rrf_k: int) -> str:
    """Build a deterministic cache key from search parameters."""
    key_data = f"{query.lower().strip()}:{lang}:{limit}:{fts_weight}:{vss_weight}:{rrf_k}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"cache:search:{key_hash}"


def get_cached_results(
    redis_client: redis.Redis,
    query: str,
    lang: str,
    limit: int,
    fts_weight: float,
    vss_weight: float,
    rrf_k: int
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Look up cached search results.

    Args:
        redis_client: Redis connection
        query: Search query
        lang: Language code
        limit: Max results
        fts_weight: FTS weight
        vss_weight: VSS weight
        rrf_k: RRF constant

    Returns:
        Tuple of (results, metadata) if cached, None otherwise
    """
    if not config.CACHE_ENABLED:
        return None

    cache_key = _build_cache_key(query, lang, limit, fts_weight, vss_weight, rrf_k)

    try:
        cached = redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            results = data.get("results") or []
            # Do not serve stale empty caches (e.g. after FT.HYBRID failure or Redis upgrade)
            if len(results) == 0:
                try:
                    redis_client.delete(cache_key)
                except Exception:
                    pass
                return None
            metadata = data.get("metadata", {})
            metadata["cache_hit"] = True
            return results, metadata
    except Exception as e:
        print(f"Cache read error: {e}")

    return None


def invalidate_search_cache(redis_client: redis.Redis) -> int:
    """
    Invalidate all cached search results.
    Called after admin creates/updates/deletes any searchable item
    so users see immediate results.

    Returns:
        Number of cache keys deleted
    """
    if not config.CACHE_ENABLED:
        return 0

    try:
        keys = redis_client.keys("cache:search:*")
        if keys:
            redis_client.delete(*keys)
            print(f"🗑️  Invalidated {len(keys)} cached search results")
            return len(keys)
    except Exception as e:
        print(f"Cache invalidation error: {e}")
    return 0


def cache_results(
    redis_client: redis.Redis,
    query: str,
    lang: str,
    limit: int,
    fts_weight: float,
    vss_weight: float,
    rrf_k: int,
    results: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> None:
    """
    Cache search results with TTL.

    Args:
        redis_client: Redis connection
        query: Search query
        lang: Language code
        limit: Max results
        fts_weight: FTS weight
        vss_weight: VSS weight
        rrf_k: RRF constant
        results: Search results to cache
        metadata: Search metadata to cache
    """
    if not config.CACHE_ENABLED:
        return

    # Avoid caching empty result sets (masks transient failures and locks users out for TTL)
    if not results:
        return

    cache_key = _build_cache_key(query, lang, limit, fts_weight, vss_weight, rrf_k)

    try:
        data = json.dumps({
            "results": results,
            "metadata": metadata
        })
        redis_client.setex(cache_key, config.CACHE_TTL, data)
    except Exception as e:
        print(f"Cache write error: {e}")
