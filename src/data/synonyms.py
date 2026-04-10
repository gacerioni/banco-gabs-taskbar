"""
Synonyms Manager
Manages Redis FT.SYNUPDATE for all indexes
"""

import redis
import json
from pathlib import Path
from typing import List, Dict


# ============================================================================
# SYNONYM LOADING
# ============================================================================

def load_synonyms() -> List[Dict[str, List[str]]]:
    """
    Load synonyms from synonyms.jsonl
    
    Format: {"group": ["word1", "word2", "word3"]}
    
    Returns:
        List of synonym groups
    """
    synonyms_file = Path(__file__).parent / "seed" / "synonyms.jsonl"
    
    if not synonyms_file.exists():
        print(f"⚠️  Synonyms file not found: {synonyms_file}")
        return []
    
    synonyms = []
    try:
        with open(synonyms_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    if 'group' in data and isinstance(data['group'], list):
                        synonyms.append(data)
        print(f"✅ Loaded {len(synonyms)} synonym groups")
    except Exception as e:
        print(f"❌ Error loading synonyms: {e}")
    
    return synonyms


# ============================================================================
# SYNONYM APPLICATION
# ============================================================================

def apply_synonyms_to_index(redis_client: redis.Redis, index_name: str) -> int:
    """
    Apply synonym groups to a specific index using FT.SYNUPDATE.
    
    Args:
        redis_client: Redis connection
        index_name: Name of the index (e.g., 'idx:routes')
        
    Returns:
        Number of synonym groups applied
    """
    synonyms = load_synonyms()
    
    if not synonyms:
        return 0
    
    count = 0
    for i, syn_data in enumerate(synonyms):
        group_id = f"syn_{i}"
        words = syn_data['group']
        
        try:
            # FT.SYNUPDATE index_name group_id word1 word2 word3...
            redis_client.execute_command(
                "FT.SYNUPDATE",
                index_name,
                group_id,
                *words
            )
            count += 1
        except Exception as e:
            print(f"⚠️  Error applying synonym group {group_id}: {e}")
    
    return count


def apply_synonyms_to_all(redis_client: redis.Redis) -> Dict[str, int]:
    """
    Apply synonyms to all indexes.
    
    Returns:
        Dict with index names and count of synonyms applied
    """
    from .models import route_schema, product_schema, sku_schema
    
    results = {}
    indexes = [
        route_schema.INDEX_NAME,
        product_schema.INDEX_NAME,
        sku_schema.INDEX_NAME,
    ]
    
    print("=" * 80)
    print("📖 Applying Synonyms to Indexes")
    print("=" * 80)
    
    for index_name in indexes:
        count = apply_synonyms_to_index(redis_client, index_name)
        results[index_name] = count
        print(f"✅ Applied {count} synonym groups to {index_name}")
    
    print("=" * 80)
    return results

