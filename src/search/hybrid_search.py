"""
Hybrid Search Module - Redis 8.6 HYBRID Search
Combines FTS (text) + VSS (vector) with native Redis scoring
"""

import redis
import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple

from .vectorizer import embed_text
from ..core.config import config


# ============================================================================
# SIMPLE TEXT SEARCH
# ============================================================================

def hybrid_search(
    redis_client: redis.Redis,
    query: str,
    lang: str = "pt",
    country: str = "BR",
    limit: int = 10,
    fts_weight: float = 0.7,
    vss_weight: float = 0.3,
    rrf_k: int = 10  # RRF constant (LOWERED from 60 to 10 for better score spread!)
) -> Tuple[List[Dict[str, Any]], float]:
    """
    NATIVE HYBRID search using Redis 8.4+ FT.HYBRID with RRF.

    Uses Redis's built-in Reciprocal Rank Fusion (RRF) to combine:
    - FTS (text) with BM25 scoring
    - VSS (vector) with cosine similarity

    This is MUCH simpler and more accurate than manual score merging!

    Args:
        redis_client: Redis connection
        query: Search query
        lang: Language code
        country: Country code
        limit: Max results
        fts_weight: FTS weight (IGNORED - RRF handles weights internally)
        vss_weight: VSS weight (IGNORED - RRF handles weights internally)
        rrf_k: RRF constant (higher = less weight on rank position)

    Returns:
        Tuple of (results, redis_time_ms)
    """
    # Generate query embedding for VSS
    print(f"🔢 Generating embedding for: {query}")
    query_embedding = embed_text(query)
    query_vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

    import re

    # Fallback values if none provided
    w_fts = fts_weight if fts_weight is not None else 0.7
    w_vss = vss_weight if vss_weight is not None else 0.3

    # Clean query for FTS (remove punctuation that could be interpreted as operators like '-' which means NOT)
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    words = [w for w in clean_query.strip().split() if w]

    if not words:
        fts_query = "*"
    else:
        fts_query = " ".join([f"{word}*" for word in words])

    # Search all indexes using FT.HYBRID
    indexes = ['idx:routes', 'idx:products', 'idx:skus']
    all_results = []
    total_redis_time = 0.0  # Track total Redis query time

    for idx_name in indexes:
        try:
            # Execute native FT.HYBRID with RRF!
            start_time = time.time()

            # FT.HYBRID syntax (count prefix = ALL tokens that follow):
            # VSIM @field $param
            #   KNN 2 K 100           -> count=2 means "K 100" (2 tokens)
            # COMBINE RRF 4 CONSTANT 60 -> count=4 means 4 tokens

            # NOTE: We reverted WEIGHTS because RediSearch 2.10.x/8.6 beta may not support
            # the WEIGHTS argument directly inside COMBINE RRF in this exact syntax yet.
            result = redis_client.execute_command(
                'FT.HYBRID', idx_name,
                'SEARCH', fts_query,
                'VSIM', '@embedding', '$vec',
                    'KNN', '2', 'K', '100',  # count=2: next 2 tokens are "K 100"
                'COMBINE', 'RRF', '2',  # count=2: next 2 tokens
                    'CONSTANT', str(rrf_k),
                'PARAMS', '2', 'vec', query_vector_bytes,
                'LIMIT', '0', str(limit)
            )

            total_redis_time += (time.time() - start_time) * 1000

            # Parse results - FT.HYBRID returns array format:
            # ['total_results', 20, 'results', [...], 'format', [...], ...]
            if isinstance(result, (list, tuple)) and len(result) >= 4:
                # Extract total_results (should be at index 1)
                total_hits = result[1] if len(result) > 1 and isinstance(result[1], int) else 0

                # Extract results array (should be at index 3)
                results_array = result[3] if len(result) > 3 and isinstance(result[3], list) else []

                print(f"🔍 {idx_name}: {total_hits} hits, {len(results_array)} results in array")

                # Parse each result from the array
                # Format: each result is a list of [field, value, field, value, ...]
                # Example: ['__key', 'sku:sku_006', '__score', 0.95, ...]
                for res_item in results_array:
                    if isinstance(res_item, list):
                        # Parse field-value pairs
                        doc_key = None
                        score = 0.0

                        # Extract __key and __score from the list
                        for i in range(0, len(res_item), 2):
                            if i + 1 < len(res_item):
                                field = res_item[i]
                                value = res_item[i + 1]

                                # Convert bytes to string if needed
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

                        # Fetch document if we got the key
                        if doc_key:
                            try:
                                doc = redis_client.json().get(doc_key)
                                if doc:
                                    doc.pop('embedding', None)
                                    doc['_hybrid_score'] = score
                                    doc['match_type'] = 'hybrid_rrf'
                                    all_results.append(doc)
                                    print(f"   ✅ Added: {doc.get('title', doc_key)} (score: {score:.4f})")
                            except Exception as e:
                                print(f"⚠️  Error getting {doc_key}: {e}")

        except Exception as e:
            print(f"⚠️  FT.HYBRID error on {idx_name}: {e}")

    # POST-PROCESSING: Apply relevance boost for exact/partial matches
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())

    for doc in all_results:
        title = doc.get('title', '').lower().strip()
        original_score = doc['_hybrid_score']

        # EXACT MATCH = 10x boost!
        if title == query_lower:
            doc['_hybrid_score'] *= 10.0
            print(f"🎯 EXACT MATCH BOOST: '{doc.get('title')}' {original_score:.4f} → {doc['_hybrid_score']:.4f}")

        # PARTIAL MATCH (all query words in title) = 3x boost
        elif query_words and all(word in title for word in query_words):
            doc['_hybrid_score'] *= 3.0
            print(f"📍 PARTIAL MATCH BOOST: '{doc.get('title')}' {original_score:.4f} → {doc['_hybrid_score']:.4f}")

    # Sort all results by boosted hybrid score and return top N
    all_results.sort(key=lambda x: x.get('_hybrid_score', 0), reverse=True)

    # Debug: print top results
    print(f"\n📊 Top {min(5, len(all_results))} results for '{query}':")
    for i, doc in enumerate(all_results[:5]):
        title = doc.get('title', 'N/A')
        score = doc.get('_hybrid_score', 0)
        print(f"  {i+1}. {title} (score: {score})")

    print(f"⚡ Redis search time: {total_redis_time:.2f}ms")

    return all_results[:limit], round(total_redis_time, 2)

