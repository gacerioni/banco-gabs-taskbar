"""
Route Index Schema - Redis 8.6 HYBRID Search
Banking routes index with optimized field weights and hybrid scoring
"""

import redis
from typing import Dict, Any, Optional


# ============================================================================
# INDEX CONFIGURATION
# ============================================================================

INDEX_NAME = "idx:routes"
INDEX_PREFIX = "route:"

# Field weights for FTS (production-optimized)
FIELD_WEIGHTS = {
    "title": 10.0,      # Highest - route name is most important
    "subtitle": 5.0,    # High - description matters
    "description": 1.0, # Base weight
    "tags": 3.0,        # Medium - keywords important
    "keywords": 7.0,    # Very high - real user queries (common search terms)
    "aliases": 5.0,     # High - common variations and typos
    # synonyms removed - using Redis global synonyms (FT.SYNUPDATE) instead!
}

# Hybrid search weights (configurable via config)
# Will be overridden by config.py values
DEFAULT_FTS_WEIGHT = 0.7  # 70% text relevance
DEFAULT_VSS_WEIGHT = 0.3  # 30% semantic similarity


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

def get_schema_fields() -> list:
    """
    Define FT.CREATE schema fields for routes index.

    Returns:
        List of field definitions for Redis FT.CREATE
    """
    from ...core.config import config

    return [
        # Text fields with weights (JSONPath format)
        "$.title", "AS", "title", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["title"]),
        "$.subtitle", "AS", "subtitle", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["subtitle"]),
        "$.description", "AS", "description", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["description"]),
        "$.tags", "AS", "tags", "TAG", "SEPARATOR", ",",

        # Search optimization fields (user queries, variations)
        "$.keywords", "AS", "keywords", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["keywords"]),
        "$.aliases", "AS", "aliases", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["aliases"]),
        # synonyms field removed - using Redis global synonyms instead!

        # Metadata fields
        "$.type", "AS", "type", "TAG",
        "$.id", "AS", "id", "TAG",
        "$.lang", "AS", "lang", "TAG",
        "$.country", "AS", "country", "TAG",

        # Vector field for semantic search (dims from config)
        "$.embedding", "AS", "embedding", "VECTOR", "FLAT", "6",
        "TYPE", "FLOAT32",
        "DIM", str(config.EMBEDDING_DIM),
        "DISTANCE_METRIC", "COSINE"
    ]


# ============================================================================
# INDEX MANAGEMENT
# ============================================================================

def create_index(redis_client: redis.Redis) -> bool:
    """
    Create routes index with HYBRID search support (Redis 8.6+).
    
    Features:
    - FTS with weighted fields (title > subtitle > description)
    - Vector search (Qwen3 4096-dim embeddings)
    - HYBRID scoring (native Redis 8.6)
    - Language and country filtering
    
    Args:
        redis_client: Redis connection
        
    Returns:
        True if created, False if already exists
    """
    try:
        # Check if index exists
        redis_client.execute_command("FT.INFO", INDEX_NAME)
        print(f"⚠️  Index '{INDEX_NAME}' already exists")
        return False
    except redis.exceptions.ResponseError:
        # Index doesn't exist, create it
        pass
    
    # Build FT.CREATE command
    cmd = ["FT.CREATE", INDEX_NAME]
    cmd.extend(["ON", "JSON"])
    cmd.extend(["PREFIX", "1", INDEX_PREFIX])
    cmd.extend(["SCHEMA"])
    cmd.extend(get_schema_fields())
    
    try:
        redis_client.execute_command(*cmd)
        print(f"✅ Created index '{INDEX_NAME}' with HYBRID search support")
        return True
    except Exception as e:
        print(f"❌ Error creating index '{INDEX_NAME}': {e}")
        raise


def drop_index(redis_client: redis.Redis, keep_docs: bool = False) -> bool:
    """
    Drop routes index.
    
    Args:
        redis_client: Redis connection
        keep_docs: If True, keeps documents (only drops index)
        
    Returns:
        True if dropped, False if didn't exist
    """
    try:
        if keep_docs:
            redis_client.execute_command("FT.DROPINDEX", INDEX_NAME)
        else:
            redis_client.execute_command("FT.DROPINDEX", INDEX_NAME, "DD")
        print(f"✅ Dropped index '{INDEX_NAME}'")
        return True
    except redis.exceptions.ResponseError:
        print(f"⚠️  Index '{INDEX_NAME}' doesn't exist")
        return False
    except Exception as e:
        print(f"❌ Error dropping index '{INDEX_NAME}': {e}")
        raise


def index_exists(redis_client: redis.Redis) -> bool:
    """Check if routes index exists"""
    try:
        redis_client.execute_command("FT.INFO", INDEX_NAME)
        return True
    except redis.exceptions.ResponseError:
        return False


def get_index_info(redis_client: redis.Redis) -> Optional[Dict[str, Any]]:
    """Get index information"""
    try:
        info = redis_client.execute_command("FT.INFO", INDEX_NAME)
        return dict(zip(info[::2], info[1::2]))
    except redis.exceptions.ResponseError:
        return None

