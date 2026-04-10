"""
Hybrid Search Module - Redis 8.6 NATIVE FT.HYBRID with RRF
Uses Redis 8.4+ native FT.HYBRID command with Reciprocal Rank Fusion (RRF)
This is MUCH simpler and uses Redis's native hybrid scoring!
"""

import redis
import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple

from .vectorizer import embed_text
from ..core.config import config


def hybrid_search_native(
    redis_client: redis.Redis,
    query: str,
    lang: str = "pt",
    country: str = "BR",
    limit: int = 10,
    rrf_k: int = 60  # RRF constant (default 60 is standard)
) -> Tuple[List[Dict[str, Any]], float]:
    """
    NATIVE HYBRID search using Redis 8.4+ FT.HYBRID command with RRF.
    
    Uses Reciprocal Rank Fusion (RRF) to combine:
    - FTS (text) with BM25 scoring
    - VSS (vector) with cosine similarity
    
    Args:
        redis_client: Redis connection
        query: Search query
        lang: Language code
        country: Country code
        limit: Max results
        rrf_k: RRF constant (higher = less weight on rank position)
    
    Returns:
        Tuple of (results, redis_time_ms)
    """
    # Generate query embedding for VSS
    print(f"🔢 Generating embedding for: {query}")
    query_embedding = embed_text(query)
    query_vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
    
    # Search all indexes
    indexes = ['idx:routes', 'idx:products', 'idx:skus']
    all_results = []
    total_redis_time = 0.0
    
    for idx_name in indexes:
        try:
            # Prepare FTS query (prefix matching)
            words = query.strip().split()
            fts_query = " ".join([f"{word}*" for word in words])
            
            # Execute native FT.HYBRID command
            start_time = time.time()
            
            result = redis_client.execute_command(
                'FT.HYBRID', idx_name,
                'SEARCH', fts_query,
                'VSIM', 'embedding', '$vec',
                'KNN', str(limit * 3), 'K', '100',  # Get more candidates for merging
                'COMBINE', 'RRF', str(limit * 3),
                'CONSTANT', str(rrf_k),  # RRF constant
                'YIELD_SCORE_AS', 'hybrid_score',
                'PARAMS', '2', 'vec', query_vector_bytes,
                'LIMIT', '0', str(limit * 2)
            )
            
            total_redis_time += (time.time() - start_time) * 1000
            
            # Parse results
            # Format: [total, doc1_key, [fields...], doc2_key, [fields...], ...]
            total_hits = result[0]
            
            if total_hits > 0:
                i = 1
                while i < len(result):
                    doc_key = result[i]
                    
                    # Get document from Redis
                    try:
                        doc = redis_client.json().get(doc_key)
                        if doc:
                            doc.pop('embedding', None)
                            
                            # Extract hybrid score from document fields
                            # The score is in the returned fields as 'hybrid_score'
                            if i + 1 < len(result) and isinstance(result[i + 1], list):
                                fields = result[i + 1]
                                # Fields are [key1, val1, key2, val2, ...]
                                for j in range(0, len(fields), 2):
                                    if fields[j] == b'hybrid_score' or fields[j] == 'hybrid_score':
                                        try:
                                            doc['_hybrid_score'] = float(fields[j + 1])
                                        except (ValueError, TypeError, IndexError):
                                            doc['_hybrid_score'] = 0.0
                                        break
                            
                            if '_hybrid_score' not in doc:
                                doc['_hybrid_score'] = 0.0
                                
                            doc['match_type'] = 'hybrid_rrf'
                            all_results.append(doc)
                    except Exception as e:
                        print(f"⚠️  Error getting {doc_key}: {e}")
                    
                    # Move to next document
                    i += 2  # Skip doc_key and fields array
                    
        except Exception as e:
            print(f"⚠️  FT.HYBRID error on {idx_name}: {e}")
            # Fallback will be needed for older Redis versions
    
    # Sort all results by hybrid score
    all_results.sort(key=lambda x: x.get('_hybrid_score', 0), reverse=True)
    
    # Debug output
    print(f"\n📊 Top {min(5, len(all_results))} RRF results for '{query}':")
    for i, doc in enumerate(all_results[:5]):
        title = doc.get('title', 'N/A')
        score = doc.get('_hybrid_score', 0)
        print(f"  {i+1}. {title} (RRF score: {score:.4f})")
    
    print(f"⚡ Redis FT.HYBRID time: {total_redis_time:.2f}ms")
    
    return all_results[:limit], round(total_redis_time, 2)

