"""
Redis Index Manager
Centralized management of all Redis indexes
"""

import redis
from typing import Dict, List, Any

from .models import route_schema, product_schema, sku_schema


# ============================================================================
# INDEX REGISTRY
# ============================================================================

ALL_SCHEMAS = [
    route_schema,
    product_schema,
    sku_schema,
]


# ============================================================================
# INDEX MANAGEMENT
# ============================================================================

def create_all_indexes(redis_client: redis.Redis) -> Dict[str, bool]:
    """
    Create all indexes (routes, products, SKUs).
    
    Args:
        redis_client: Redis connection
        
    Returns:
        Dict with index names and creation status
        
    Example:
        {
            'idx:routes': True,
            'idx:products': True,
            'idx:skus': False  # Already existed
        }
    """
    results = {}
    
    print("=" * 80)
    print("🔨 Creating Redis Indexes (HYBRID Search)")
    print("=" * 80)
    
    for schema in ALL_SCHEMAS:
        index_name = schema.INDEX_NAME
        try:
            created = schema.create_index(redis_client)
            results[index_name] = created
        except Exception as e:
            print(f"❌ Failed to create {index_name}: {e}")
            results[index_name] = False
            raise
    
    print("=" * 80)
    return results


def drop_all_indexes(redis_client: redis.Redis, keep_docs: bool = False) -> Dict[str, bool]:
    """
    Drop all indexes.
    
    Args:
        redis_client: Redis connection
        keep_docs: If True, keeps documents (only drops indexes)
        
    Returns:
        Dict with index names and drop status
    """
    results = {}
    
    print("=" * 80)
    print("🗑️  Dropping Redis Indexes")
    print("=" * 80)
    
    for schema in ALL_SCHEMAS:
        index_name = schema.INDEX_NAME
        try:
            dropped = schema.drop_index(redis_client, keep_docs=keep_docs)
            results[index_name] = dropped
        except Exception as e:
            print(f"❌ Failed to drop {index_name}: {e}")
            results[index_name] = False
    
    print("=" * 80)
    return results


def index_exists(redis_client: redis.Redis, index_name: str) -> bool:
    """
    Check if a specific index exists.
    
    Args:
        redis_client: Redis connection
        index_name: Name of the index (e.g., 'idx:routes')
        
    Returns:
        True if exists, False otherwise
    """
    try:
        redis_client.execute_command("FT.INFO", index_name)
        return True
    except redis.exceptions.ResponseError:
        return False


def get_index_info(redis_client: redis.Redis, index_name: str) -> Dict[str, Any]:
    """
    Get information about a specific index.
    
    Args:
        redis_client: Redis connection
        index_name: Name of the index
        
    Returns:
        Dict with index information
    """
    try:
        info = redis_client.execute_command("FT.INFO", index_name)
        return dict(zip(info[::2], info[1::2]))
    except redis.exceptions.ResponseError:
        return {}


def get_all_indexes_info(redis_client: redis.Redis) -> Dict[str, Dict[str, Any]]:
    """
    Get information about all indexes.
    
    Returns:
        Dict with index names as keys and their info as values
    """
    results = {}
    
    for schema in ALL_SCHEMAS:
        index_name = schema.INDEX_NAME
        results[index_name] = get_index_info(redis_client, index_name)
    
    return results


def indexes_exist_all(redis_client: redis.Redis) -> bool:
    """Check if ALL indexes exist"""
    for schema in ALL_SCHEMAS:
        if not schema.index_exists(redis_client):
            return False
    return True

