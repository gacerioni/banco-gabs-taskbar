"""
Product Index Schema - Redis 8.6 HYBRID Search
Banking products index with optimized field weights and hybrid scoring
"""

import redis
from typing import Dict, Any, Optional


# ============================================================================
# INDEX CONFIGURATION
# ============================================================================

INDEX_NAME = "idx:products"
INDEX_PREFIX = "product:"

# Field weights for FTS (production-optimized for banking products)
FIELD_WEIGHTS = {
    "title": 10.0,        # Product name is critical
    "subtitle": 5.0,      # Product tagline important
    "description": 2.0,   # Description more important than routes
    "benefits": 3.0,      # Benefits are selling points
    "tags": 4.0,          # Tags very important for products
    "keywords": 7.0,      # Real user queries (common search terms)
    "aliases": 5.0,       # Common variations (typos, abbreviations)
    # synonyms removed - using Redis global synonyms (FT.SYNUPDATE) instead!
}

# Hybrid search weights
DEFAULT_FTS_WEIGHT = 0.7
DEFAULT_VSS_WEIGHT = 0.3


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

def get_schema_fields() -> list:
    """Define FT.CREATE schema fields for products index"""
    from ...core.config import config

    return [
        # Text fields with weights (JSONPath format)
        "$.title", "AS", "title", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["title"]),
        "$.subtitle", "AS", "subtitle", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["subtitle"]),
        "$.description", "AS", "description", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["description"]),
        "$.benefits", "AS", "benefits", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["benefits"]),
        "$.tags", "AS", "tags", "TAG", "SEPARATOR", ",",

        # Search optimization fields
        "$.keywords", "AS", "keywords", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["keywords"]),
        "$.aliases", "AS", "aliases", "TEXT", "WEIGHT", str(FIELD_WEIGHTS["aliases"]),
        # synonyms field removed - using Redis global synonyms instead!

        # Metadata fields
        "$.type", "AS", "type", "TAG",
        "$.id", "AS", "id", "TAG",
        "$.category", "AS", "category", "TAG",
        "$.lang", "AS", "lang", "TAG",
        "$.country", "AS", "country", "TAG",

        # Vector field (dims from config)
        "$.embedding", "AS", "embedding", "VECTOR", "FLAT", "6",
        "TYPE", "FLOAT32",
        "DIM", str(config.EMBEDDING_DIM),
        "DISTANCE_METRIC", "COSINE"
    ]


# ============================================================================
# INDEX MANAGEMENT
# ============================================================================

def create_index(redis_client: redis.Redis) -> bool:
    """Create products index with HYBRID search support"""
    try:
        redis_client.execute_command("FT.INFO", INDEX_NAME)
        print(f"⚠️  Index '{INDEX_NAME}' already exists")
        return False
    except redis.exceptions.ResponseError:
        pass
    
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
    """Drop products index"""
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
    """Check if products index exists"""
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

