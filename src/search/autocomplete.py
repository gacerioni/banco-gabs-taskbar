"""
Autocomplete Module
Redis FT.SUGGET autocomplete functionality
"""

import redis
from typing import List, Dict, Any

from ..data.seed.loader import load_routes, load_products, load_skus


# ============================================================================
# AUTOCOMPLETE SETUP
# ============================================================================

def setup_autocomplete(redis_client: redis.Redis) -> int:
    """
    Populate autocomplete dictionary using FT.SUGADD.
    Creates suggestions from titles with payload linking to document ID.
    
    Returns:
        Number of suggestions added
    """
    print("=" * 80)
    print("🔍 Setting up Autocomplete")
    print("=" * 80)
    
    ac_key = "ac:taskbar"
    count = 0
    
    # Load all data
    routes = load_routes()
    products = load_products()
    skus = load_skus()
    
    all_docs = routes + products + skus
    
    for doc in all_docs:
        title = doc.get('title', '').strip()
        doc_id = doc.get('id', '')
        doc_type = doc.get('type', '')
        
        if title and doc_id:
            try:
                # FT.SUGADD key suggestion score [PAYLOAD payload]
                # Score based on popularity or default
                score = doc.get('popularity', 1.0)
                payload = f"{doc_type}:{doc_id}"
                
                redis_client.execute_command(
                    "FT.SUGADD",
                    ac_key,
                    title,
                    score,
                    "PAYLOAD",
                    payload
                )
                count += 1
            except Exception as e:
                print(f"⚠️  Error adding suggestion '{title}': {e}")
    
    print(f"✅ Added {count} autocomplete suggestions")
    print("=" * 80)
    return count


# ============================================================================
# AUTOCOMPLETE SEARCH
# ============================================================================

def autocomplete_search(redis_client: redis.Redis, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get autocomplete suggestions using FT.SUGGET.
    
    Args:
        redis_client: Redis connection
        query: User input prefix (minimum 2 characters)
        limit: Maximum number of suggestions
        
    Returns:
        List of suggestions with payload
        
    Example:
        [
            {
                "suggestion": "Pix",
                "score": 10.5,
                "payload": "route:pix_001"
            }
        ]
    """
    if len(query) < 2:
        return []
    
    ac_key = "ac:taskbar"
    
    try:
        # FT.SUGGET key prefix [FUZZY] [WITHSCORES] [WITHPAYLOADS] [MAX num]
        result = redis_client.execute_command(
            "FT.SUGGET",
            ac_key,
            query,
            "FUZZY",
            "WITHSCORES",
            "WITHPAYLOADS",
            "MAX",
            str(limit)
        )
        
        # Parse result: [suggestion1, score1, payload1, suggestion2, score2, payload2, ...]
        suggestions = []
        for i in range(0, len(result), 3):
            suggestions.append({
                "suggestion": result[i],
                "score": float(result[i + 1]),
                "payload": result[i + 2]
            })
        
        return suggestions
    
    except Exception as e:
        print(f"❌ Autocomplete error: {e}")
        return []

