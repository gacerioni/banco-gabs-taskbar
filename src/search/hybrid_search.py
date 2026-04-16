"""
Hybrid Search Module - Redis 8.6 HYBRID Search
Combines FTS (text) + VSS (vector) with native Redis scoring
Includes latency breakdown, match explanations, and spellcheck fallback
"""

import redis
import numpy as np
import time
import re
from typing import List, Dict, Any, Tuple, Optional

from .vectorizer import embed_text
from .spellcheck import spellcheck_query
from ..core.config import config


# ============================================================================
# MATCH EXPLANATION
# ============================================================================

def _build_match_explanation(doc: Dict[str, Any], query: str, boost_type: str = None, original_score: float = None) -> str:
    """
    Build a human-readable explanation of why this result matched.

    Args:
        doc: The result document
        query: Original search query
        boost_type: 'exact', 'partial', or None
        original_score: The original RRF score before any boost multiplier

    Returns:
        Explanation string
    """
    parts = []
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())

    # Check for keyword overlap (FTS indicator)
    keywords = doc.get('keywords', '').lower() if isinstance(doc.get('keywords'), str) else ''
    aliases = doc.get('aliases', '').lower() if isinstance(doc.get('aliases'), str) else ''

    keyword_matches = [w for w in query_words if w in keywords or w in aliases]
    if keyword_matches:
        parts.append(f"Keyword: '{', '.join(keyword_matches)}'")

    # Check for title word overlap
    title = doc.get('title', '').lower()
    title_words = set(title.split())
    title_overlap = query_words & title_words
    if title_overlap and not keyword_matches:
        parts.append(f"Title match: '{', '.join(title_overlap)}'")

    # Boost type
    if boost_type == 'exact':
        parts.append("Exact title match (10x boost)")
    elif boost_type == 'partial':
        parts.append("Partial title match (3x boost)")

    # Use original (pre-boost) RRF score if provided, otherwise read from doc
    score = original_score if original_score is not None else doc.get('_hybrid_score', 0)
    parts.append(f"RRF score: {score:.4f}")

    # Doc type
    doc_type = doc.get('type', 'unknown')
    parts.append(f"Type: {doc_type}")

    return " | ".join(parts) if parts else f"Hybrid match (score: {score:.4f})"


# ============================================================================
# HYBRID SEARCH
# ============================================================================

DEFAULT_HYBRID_INDEXES = ["idx:routes", "idx:products", "idx:skus"]


def build_fts_prefix_query(query: str) -> str:
    """
    Build the same prefix FTS clause used inside FT.HYBRID (for concierge-only SKU text assist).
    """
    clean_query = re.sub(r"[^\w\s]", " ", query or "")
    words = [w for w in clean_query.strip().split() if w]
    if not words:
        return "*"
    return " ".join([f"{word}*" for word in words])


def hybrid_search(
    redis_client: redis.Redis,
    query: str,
    lang: str = "pt",
    country: str = "BR",
    limit: int = 10,
    fts_weight: float = 0.7,
    vss_weight: float = 0.3,
    rrf_k: int = 10,  # RRF constant (LOWERED from 60 to 10 for better score spread!)
    indexes: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    NATIVE HYBRID search using Redis 8.4+ FT.HYBRID with RRF.

    Uses Redis's built-in Reciprocal Rank Fusion (RRF) to combine:
    - FTS (text) with BM25 scoring
    - VSS (vector) with cosine similarity

    Includes:
    - Latency breakdown (embedding_ms, redis_search_ms, post_processing_ms)
    - Match explanations per result
    - Spellcheck fallback when 0 results

    Args:
        redis_client: Redis connection
        query: Search query
        lang: Language code
        country: Country code
        limit: Max results
        fts_weight: FTS weight (passed through for metadata)
        vss_weight: VSS weight (passed through for metadata)
        rrf_k: RRF constant (higher = less weight on rank position)
        indexes: RediSearch index names to query (default: routes, products, skus).
            Pass e.g. ``["idx:skus"]`` for marketplace-only concierge search.

    Returns:
        Tuple of (results, search_metadata) where search_metadata includes
        timing breakdown, spellcheck suggestions, etc.
    """
    search_metadata = {
        "embedding_ms": 0.0,
        "redis_search_ms": 0.0,
        "post_processing_ms": 0.0,
        "spellcheck_ms": 0.0,
        "total_redis_ms": 0.0,
        "spellcheck_suggestions": [],
        "corrected_query": None,
        "cache_hit": False,
    }

    # Generate query embedding for VSS
    print(f"Generating embedding for: {query}")
    embed_start = time.time()
    query_embedding = embed_text(query)
    query_vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
    search_metadata["embedding_ms"] = round((time.time() - embed_start) * 1000, 2)

    fts_query = build_fts_prefix_query(query)

    # Search selected indexes using FT.HYBRID
    index_list = indexes if indexes is not None else DEFAULT_HYBRID_INDEXES
    all_results = []
    total_redis_time = 0.0

    # Phase 1: Run FT.HYBRID on all indexes and collect doc keys + scores
    doc_keys_scores = []  # list of (doc_key, score)

    redis_start = time.time()
    for idx_name in index_list:
        try:
            start_time = time.time()

            result = redis_client.execute_command(
                'FT.HYBRID', idx_name,
                'SEARCH', fts_query,
                'VSIM', '@embedding', '$vec',
                    'KNN', '2', 'K', '100',
                'COMBINE', 'RRF', '2',
                    'CONSTANT', str(rrf_k),
                'PARAMS', '2', 'vec', query_vector_bytes,
                'LIMIT', '0', str(limit)
            )

            total_redis_time += (time.time() - start_time) * 1000

            # Parse results - FT.HYBRID returns array format
            if isinstance(result, (list, tuple)) and len(result) >= 4:
                total_hits = result[1] if len(result) > 1 and isinstance(result[1], int) else 0
                results_array = result[3] if len(result) > 3 and isinstance(result[3], list) else []

                print(f"{idx_name}: {total_hits} hits, {len(results_array)} results in array")

                for res_item in results_array:
                    if isinstance(res_item, list):
                        doc_key = None
                        score = 0.0

                        for i in range(0, len(res_item), 2):
                            if i + 1 < len(res_item):
                                field = res_item[i]
                                value = res_item[i + 1]

                                if isinstance(field, bytes):
                                    field = field.decode()
                                if isinstance(value, bytes):
                                    value = value.decode()

                                if field == '__key':
                                    doc_key = value
                                elif field == '__score':
                                    try:
                                        score = float(value)
                                    except (ValueError, TypeError):
                                        score = 0.0

                        if doc_key:
                            doc_keys_scores.append((doc_key, score))

        except Exception as e:
            print(f"FT.HYBRID error on {idx_name}: {e}")

    # Phase 2: Batch-fetch all documents using a Redis pipeline (1 round-trip
    # instead of N individual JSON.GET calls — critical for Redis Cloud latency)
    if doc_keys_scores:
        pipe = redis_client.pipeline(transaction=False)
        for doc_key, _ in doc_keys_scores:
            pipe.json().get(doc_key)

        fetch_start = time.time()
        try:
            docs = pipe.execute(raise_on_error=False)
        except Exception as e:
            print(f"Pipeline fetch error: {e}")
            docs = []
        total_redis_time += (time.time() - fetch_start) * 1000

        for (doc_key, score), doc in zip(doc_keys_scores, docs):
            if doc and isinstance(doc, dict):
                doc.pop('embedding', None)
                doc['_hybrid_score'] = score
                doc['match_type'] = 'hybrid_rrf'
                all_results.append(doc)

    search_metadata["redis_search_ms"] = round((time.time() - redis_start) * 1000, 2)
    search_metadata["total_redis_ms"] = round(total_redis_time, 2)

    # SPELLCHECK FALLBACK: If no results, try spellcheck
    if not all_results:
        spell_start = time.time()
        corrections = spellcheck_query(redis_client, query, index_list)

        if corrections:
            search_metadata["spellcheck_suggestions"] = corrections
            # Build corrected query from already-fetched corrections (avoids double Redis call)
            corrected = query
            for correction in corrections:
                corrected = corrected.replace(correction['original'], correction['suggestion'])
            search_metadata["corrected_query"] = corrected
            print(f"Spellcheck: '{query}' -> '{corrected}'")

        search_metadata["spellcheck_ms"] = round((time.time() - spell_start) * 1000, 2)

    # POST-PROCESSING: Apply relevance boost for exact/partial matches
    post_start = time.time()
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())

    for doc in all_results:
        title = doc.get('title', '').lower().strip()
        original_score = doc['_hybrid_score']
        boost_type = None

        # EXACT MATCH = 10x boost!
        if title == query_lower:
            doc['_hybrid_score'] *= 10.0
            boost_type = 'exact'
            print(f"EXACT MATCH BOOST: '{doc.get('title')}' {original_score:.4f} -> {doc['_hybrid_score']:.4f}")

        # PARTIAL MATCH (all query words in title) = 3x boost
        elif query_words and all(word in title for word in query_words):
            doc['_hybrid_score'] *= 3.0
            boost_type = 'partial'
            print(f"PARTIAL MATCH BOOST: '{doc.get('title')}' {original_score:.4f} -> {doc['_hybrid_score']:.4f}")

        # Add match explanation (pass original_score so RRF score is pre-boost)
        doc['match_explanation'] = _build_match_explanation(doc, query, boost_type, original_score)

    # Sort all results by boosted hybrid score and return top N
    all_results.sort(key=lambda x: x.get('_hybrid_score', 0), reverse=True)
    search_metadata["post_processing_ms"] = round((time.time() - post_start) * 1000, 2)

    # Debug: print top results
    print(f"\nTop {min(5, len(all_results))} results for '{query}':")
    for i, doc in enumerate(all_results[:5]):
        title = doc.get('title', 'N/A')
        score = doc.get('_hybrid_score', 0)
        explanation = doc.get('match_explanation', '')
        print(f"  {i+1}. {title} (score: {score}) [{explanation}]")

    print(f"Redis search time: {total_redis_time:.2f}ms")

    return all_results[:limit], search_metadata

