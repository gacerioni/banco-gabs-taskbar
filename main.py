"""
Banco Inter Task Bar MVP - Global Search for Customer 360
Fast hybrid search (text + vector) for routes, marketplace SKUs, and banking products
Uses Redis 8 + RediSearch + RedisVL SemanticRouter for intelligent intent detection
"""

import json
import time
import struct
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

import redis
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

# RedisVL imports for semantic routing
from redisvl.extensions.router import Route, SemanticRouter, RoutingConfig
from redisvl.extensions.router.schema import DistanceAggregationMethod
from redisvl.utils.vectorize import HFTextVectorizer

# ============================================================================
# CONFIGURATION
# ============================================================================

from config import config

# Extract configuration
EMBEDDING_DIM = config.EMBEDDING_DIM
DEFAULT_LIMIT = config.DEFAULT_LIMIT
POPULARITY_WEIGHT = config.POPULARITY_WEIGHT

# Vector search configuration
VECTOR_ALGORITHM = "HNSW"
DISTANCE_METRIC = "COSINE"

# Search configuration
ROUTE_BOOST = 1.5  # Boost routes over products/SKUs for ambiguous queries

# ============================================================================
# REDIS CONNECTION
# ============================================================================

# Connect to Redis using URL (supports authentication)
redis_client = redis.from_url(
    config.REDIS_URL,
    decode_responses=False  # We need binary for vectors
)

REDIS_URL = config.REDIS_URL

# ============================================================================
# SEMANTIC ROUTER (RedisVL) - Dynamic Intent Detection
# ============================================================================
# DISABLED: Simplified to parallel search approach - preserved for future use
# The semantic router adds ~20-30ms latency for only 3 small indexes (~40 docs total)
# Redis is fast enough to search all indexes in parallel (~5-10ms total)
# Keeping this code commented out in case we need it for larger scale or A/B testing

"""
# Global semantic router instance (initialized after data seeding)
semantic_router: Optional[SemanticRouter] = None

def initialize_semantic_router():
    '''
    Initialize RedisVL SemanticRouter by learning from JSONL data files.

    Strategy:
    - Automatically extracts semantic references from routes.jsonl, skus.jsonl, products.jsonl
    - Uses title, description, keywords, and aliases as training references
    - No hardcoded references - fully data-driven!
    - Easy to maintain: just update JSONL files, no code changes needed
    '''
    global semantic_router

    try:
        # Extract references from data files
        route_references = extract_references_from_file("routes.jsonl")
        sku_references = extract_references_from_file("skus.jsonl")
        product_references = extract_references_from_file("products.jsonl")

        print(f"📚 Learned {len(route_references)} route references")
        print(f"📚 Learned {len(sku_references)} SKU references")
        print(f"📚 Learned {len(product_references)} product references")

        # Create semantic routes from learned data
        route_route = Route(
            name="route",
            references=route_references,
            metadata={"type": "banking_action", "source": "routes.jsonl"},
            distance_threshold=0.55  # Stricter - only match clear banking intents
        )

        sku_route = Route(
            name="sku",
            references=sku_references,
            metadata={"type": "marketplace_product", "source": "skus.jsonl"},
            distance_threshold=0.58  # Stricter - avoid false positives
        )

        product_route = Route(
            name="product",
            references=product_references,
            metadata={"type": "banking_product", "source": "products.jsonl"},
            distance_threshold=0.60  # Stricter - banking products need precision
        )

        # Initialize semantic router with shared vectorizer
        semantic_router = SemanticRouter(
            name="banco-inter-intent-router",
            vectorizer=get_vectorizer(),  # Use shared vectorizer
            routes=[route_route, sku_route, product_route],
            routing_config=RoutingConfig(
                max_k=2,  # Return top 2 matches for ambiguity detection
                aggregation_method=DistanceAggregationMethod.avg
            ),
            redis_url=REDIS_URL,
            overwrite=True  # Recreate on each startup
        )

        print("✅ Semantic router initialized successfully (data-driven)")
        return True

    except Exception as e:
        print(f"⚠️  Semantic router initialization failed: {e}")
        print("   Falling back to keyword-based intent detection")
        return False
"""

def extract_references_from_file(filename: str) -> List[str]:
    """
    Extract semantic references from a JSONL data file.

    Extracts from:
    - title (main reference)
    - description (context)
    - keywords (explicit tags)
    - aliases (variations)

    Returns a deduplicated list of reference strings.
    """
    references = []
    filepath = Path(__file__).parent / filename

    if not filepath.exists():
        print(f"⚠️  File not found: {filename}")
        return references

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)

                # Extract title (primary reference)
                if 'title' in doc and doc['title']:
                    references.append(doc['title'].lower())

                # Extract description (semantic context)
                if 'description' in doc and doc['description']:
                    references.append(doc['description'].lower())

                # Extract keywords (explicit tags)
                if 'keywords' in doc and isinstance(doc['keywords'], list):
                    references.extend([kw.lower() for kw in doc['keywords'] if kw])

                # Extract aliases (variations)
                if 'aliases' in doc and isinstance(doc['aliases'], list):
                    references.extend([alias.lower() for alias in doc['aliases'] if alias])

                # Extract subtitle (additional context)
                if 'subtitle' in doc and doc['subtitle']:
                    references.append(doc['subtitle'].lower())

            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error in {filename}: {e}")
                continue

    # Deduplicate and filter empty strings
    references = list(set([ref.strip() for ref in references if ref and ref.strip()]))

    return references

# ============================================================================
# EMBEDDING FUNCTION (Pluggable)
# ============================================================================

# Global vectorizer instance (shared with SemanticRouter)
_vectorizer: Optional[HFTextVectorizer] = None

def get_vectorizer() -> HFTextVectorizer:
    """
    Get or create the shared HFTextVectorizer instance.
    Uses the same model as RedisVL SemanticRouter for consistency.
    """
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = HFTextVectorizer(
            model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _vectorizer

def embed_text_real(text: str) -> np.ndarray:
    """
    Real embedding function using HuggingFace sentence-transformers.
    Uses the same model as RedisVL SemanticRouter.
    """
    vectorizer = get_vectorizer()
    # HFTextVectorizer.embed returns a list of floats
    embedding = vectorizer.embed(text)
    return np.array(embedding, dtype=np.float32)

def embed_text_stub(text: str) -> np.ndarray:
    """
    Stub embedding function - generates deterministic fake embeddings.
    Fallback when real embeddings are not available.
    """
    # Simple hash-based fake embedding for demo
    np.random.seed(hash(text.lower()) % (2**32))
    embedding = np.random.randn(EMBEDDING_DIM).astype(np.float32)
    # Normalize for cosine similarity
    embedding = embedding / np.linalg.norm(embedding)
    return embedding

# Global embedding function (defaults to real, falls back to stub)
embed_function: Callable[[str], np.ndarray] = embed_text_real

def set_embedding_function(func: Callable[[str], np.ndarray]):
    """Allow swapping embedding function at runtime"""
    global embed_function
    embed_function = func

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def vector_to_bytes(vector: np.ndarray) -> bytes:
    """Convert numpy array to bytes for Redis storage"""
    return struct.pack(f'{len(vector)}f', *vector.tolist())

def bytes_to_vector(data: bytes) -> np.ndarray:
    """Convert bytes from Redis to numpy array"""
    return np.array(struct.unpack(f'{len(data)//4}f', data))

def create_search_text(doc: Dict[str, Any]) -> str:
    """Create comprehensive search text from document"""
    parts = [
        doc.get('title', ''),
        doc.get('description', ''),
        ' '.join(doc.get('keywords', [])),
        ' '.join(doc.get('aliases', []))
    ]
    return ' '.join(filter(None, parts))

# ============================================================================
# REDIS SCHEMA & INDEXING
# ============================================================================

def create_indexes():
    """
    Create RediSearch indexes for routes, SKUs, and products
    Uses hybrid indexing: TEXT fields + VECTOR field for semantic search
    """
    try:
        # Drop existing indexes
        for idx_name in ['idx:routes', 'idx:skus', 'idx:products']:
            try:
                redis_client.execute_command('FT.DROPINDEX', idx_name, 'DD')
            except:
                pass
        
        # Create Routes Index
        redis_client.execute_command(
            'FT.CREATE', 'idx:routes',
            'ON', 'JSON',
            'PREFIX', '1', 'route:',
            'SCHEMA',
            '$.title', 'AS', 'title', 'TEXT', 'WEIGHT', '3.0',
            '$.subtitle', 'AS', 'subtitle', 'TEXT', 'WEIGHT', '1.5',
            '$.description', 'AS', 'description', 'TEXT', 'WEIGHT', '1.0',
            '$.keywords[*]', 'AS', 'keywords', 'TEXT', 'WEIGHT', '2.0',
            '$.aliases', 'AS', 'aliases', 'TEXT', 'WEIGHT', '2.5',  # Changed from $.aliases[*] to $.aliases (it's a string, not array)
            '$.category', 'AS', 'category', 'TAG',
            '$.lang', 'AS', 'lang', 'TAG',
            '$.country', 'AS', 'country', 'TAG',
            '$.popularity', 'AS', 'popularity', 'NUMERIC', 'SORTABLE',
            '$.embedding', 'AS', 'embedding', 'VECTOR', VECTOR_ALGORITHM, '6',
            'TYPE', 'FLOAT32', 'DIM', str(EMBEDDING_DIM), 'DISTANCE_METRIC', DISTANCE_METRIC
        )
        
        # Create SKUs Index
        redis_client.execute_command(
            'FT.CREATE', 'idx:skus',
            'ON', 'JSON',
            'PREFIX', '1', 'sku:',
            'SCHEMA',
            '$.title', 'AS', 'title', 'TEXT', 'WEIGHT', '3.0',
            '$.subtitle', 'AS', 'subtitle', 'TEXT', 'WEIGHT', '1.0',
            '$.description', 'AS', 'description', 'TEXT', 'WEIGHT', '1.5',
            '$.keywords[*]', 'AS', 'keywords', 'TEXT', 'WEIGHT', '2.0',
            '$.brand', 'AS', 'brand', 'TEXT', 'WEIGHT', '2.0',
            '$.category', 'AS', 'category', 'TAG',
            '$.subcategory', 'AS', 'subcategory', 'TAG',
            '$.lang', 'AS', 'lang', 'TAG',
            '$.country', 'AS', 'country', 'TAG',
            '$.price', 'AS', 'price', 'NUMERIC', 'SORTABLE',
            '$.cashback', 'AS', 'cashback', 'NUMERIC', 'SORTABLE',
            '$.popularity', 'AS', 'popularity', 'NUMERIC', 'SORTABLE',
            '$.in_stock', 'AS', 'in_stock', 'TAG',
            '$.embedding', 'AS', 'embedding', 'VECTOR', VECTOR_ALGORITHM, '6',
            'TYPE', 'FLOAT32', 'DIM', str(EMBEDDING_DIM), 'DISTANCE_METRIC', DISTANCE_METRIC
        )
        
        # Create Products Index
        redis_client.execute_command(
            'FT.CREATE', 'idx:products',
            'ON', 'JSON',
            'PREFIX', '1', 'product:',
            'SCHEMA',
            '$.title', 'AS', 'title', 'TEXT', 'WEIGHT', '3.0',
            '$.subtitle', 'AS', 'subtitle', 'TEXT', 'WEIGHT', '1.5',
            '$.description', 'AS', 'description', 'TEXT', 'WEIGHT', '1.5',
            '$.keywords[*]', 'AS', 'keywords', 'TEXT', 'WEIGHT', '2.0',
            '$.aliases', 'AS', 'aliases', 'TEXT', 'WEIGHT', '2.5',  # Changed from $.aliases[*] to $.aliases (it's a string, not array)
            '$.category', 'AS', 'category', 'TAG',
            '$.lang', 'AS', 'lang', 'TAG',
            '$.country', 'AS', 'country', 'TAG',
            '$.popularity', 'AS', 'popularity', 'NUMERIC', 'SORTABLE',
            '$.embedding', 'AS', 'embedding', 'VECTOR', VECTOR_ALGORITHM, '6',
            'TYPE', 'FLOAT32', 'DIM', str(EMBEDDING_DIM), 'DISTANCE_METRIC', DISTANCE_METRIC
        )

        print("✅ Indexes created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False

# ============================================================================
# DATA SEEDING
# ============================================================================

def seed_data(routes_file: str = "routes.jsonl",
              skus_file: str = "skus.jsonl",
              products_file: str = "products.jsonl"):
    """Load JSONL files into Redis with embeddings"""

    start_time = time.time()
    counts = {'routes': 0, 'skus': 0, 'products': 0}

    # Load routes
    if Path(routes_file).exists():
        with open(routes_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                doc = json.loads(line)
                doc_id = doc['id']

                # Generate embedding
                search_text = create_search_text(doc)
                embedding = embed_function(search_text)
                doc['embedding'] = embedding.tolist()

                # Store as JSON
                redis_client.execute_command(
                    'JSON.SET', f'route:{doc_id}', '$', json.dumps(doc)
                )
                counts['routes'] += 1

    # Load SKUs
    if Path(skus_file).exists():
        with open(skus_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                doc = json.loads(line)
                doc_id = doc['id']

                # Generate embedding
                search_text = create_search_text(doc)
                embedding = embed_function(search_text)
                doc['embedding'] = embedding.tolist()

                # Store as JSON
                redis_client.execute_command(
                    'JSON.SET', f'sku:{doc_id}', '$', json.dumps(doc)
                )
                counts['skus'] += 1

    # Load products
    if Path(products_file).exists():
        with open(products_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                doc = json.loads(line)
                doc_id = doc['id']

                # Generate embedding
                search_text = create_search_text(doc)
                embedding = embed_function(search_text)
                doc['embedding'] = embedding.tolist()

                # Store as JSON
                redis_client.execute_command(
                    'JSON.SET', f'product:{doc_id}', '$', json.dumps(doc)
                )
                counts['products'] += 1

    elapsed = time.time() - start_time
    print(f"✅ Seeded {counts['routes']} routes, {counts['skus']} SKUs, {counts['products']} products in {elapsed:.2f}s")
    return counts

# ============================================================================
# AUTOCOMPLETE & SYNONYMS (Cactus Gaming approach)
# ============================================================================

def setup_autocomplete():
    """
    Populate autocomplete dictionary using FT.SUGADD.
    Creates suggestions from titles and aliases with PAYLOAD linking to document ID.
    """
    print("🔍 Setting up autocomplete...")

    ac_key = "ac:taskbar"
    suggestion_count = 0

    # Clear existing autocomplete
    try:
        redis_client.delete(ac_key)
    except:
        pass

    # Process all document types
    for jsonl_file, doc_type in [('routes.jsonl', 'route'), ('skus.jsonl', 'sku'), ('products.jsonl', 'product')]:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                doc = json.loads(line)
                doc_id = doc['id']
                popularity = doc.get('popularity', 50)

                # Add main title
                try:
                    redis_client.execute_command(
                        'FT.SUGADD', ac_key,
                        doc['title'],
                        popularity,
                        'PAYLOAD', doc_id
                    )
                    suggestion_count += 1
                except:
                    pass  # Skip duplicates

                # Add individual alias tokens
                aliases = doc.get('aliases', '')
                if aliases:
                    for alias in aliases.split():
                        if len(alias) > 2:  # Skip very short tokens
                            try:
                                redis_client.execute_command(
                                    'FT.SUGADD', ac_key,
                                    alias,
                                    popularity,
                                    'PAYLOAD', doc_id
                                )
                                suggestion_count += 1
                            except:
                                pass  # Skip duplicates

    print(f"✅ {suggestion_count} autocomplete suggestions added")
    return suggestion_count


def setup_synonyms():
    """
    Create synonym groups using FT.SYNUPDATE.
    Reads synonyms directly from JSONL files (single source of truth).
    Synonyms are automatically expanded during FT.SEARCH.
    """
    print("🔤 Setting up synonym groups from JSONLs...")

    # Collect all unique synonym groups from all documents
    synonym_groups = {}  # {frozenset(terms): [terms]}

    # Process all document types
    for jsonl_file in ['routes.jsonl', 'skus.jsonl', 'products.jsonl']:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                doc = json.loads(line)
                synonyms = doc.get('synonyms', [])

                if synonyms and len(synonyms) > 1:
                    # Create a unique key from the synonym set
                    syn_key = frozenset(synonyms)
                    if syn_key not in synonym_groups:
                        synonym_groups[syn_key] = synonyms

    # Apply synonyms to all indexes
    group_count = 0
    for idx_name in ['idx:routes', 'idx:skus', 'idx:products']:
        for idx, terms in enumerate(synonym_groups.values()):
            try:
                # Generate unique group ID
                group_id = f"syn:{idx}"
                redis_client.execute_command(
                    'FT.SYNUPDATE', idx_name, group_id, *terms
                )
                group_count += 1
            except Exception as e:
                print(f"⚠️  Error adding synonym group to {idx_name}: {e}")

    print(f"✅ {len(synonym_groups)} unique synonym groups configured across all indexes")
    return len(synonym_groups)


def get_autocomplete_suggestions(prefix: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Get autocomplete suggestions using FT.SUGGET.

    Args:
        prefix: User input prefix (minimum 2 characters)
        max_results: Maximum number of suggestions

    Returns:
        List of suggestion dictionaries with text, score, and doc_id
    """
    if not prefix or len(prefix) < 2:
        return []

    try:
        # FT.SUGGET ac:taskbar <prefix> WITHPAYLOADS WITHSCORES FUZZY MAX <max>
        results = redis_client.execute_command(
            'FT.SUGGET', 'ac:taskbar',
            prefix,
            'WITHPAYLOADS',
            'WITHSCORES',
            'FUZZY',
            'MAX', max_results
        )

        # Parse results: [suggestion, score, payload, suggestion, score, payload, ...]
        suggestions = []
        for i in range(0, len(results), 3):
            if i + 2 < len(results):
                suggestions.append({
                    'text': results[i].decode('utf-8') if isinstance(results[i], bytes) else results[i],
                    'score': float(results[i + 1]),
                    'doc_id': results[i + 2].decode('utf-8') if isinstance(results[i + 2], bytes) else results[i + 2]
                })

        return suggestions
    except Exception as e:
        print(f"Autocomplete error: {e}")
        return []

# ============================================================================
# SEARCH LOGIC
# ============================================================================

"""
# DISABLED: Semantic intent detection - preserved for future use
# Using parallel search approach instead (faster and simpler for small dataset)

def detect_intent_semantic(query: str) -> tuple[str, Optional[float], str]:
    '''
    Semantic intent detection using RedisVL SemanticRouter.

    Returns: (intent, confidence, strategy)
        - intent: 'route', 'sku', 'product', or 'mixed'
        - confidence: distance score (0-2, lower is better) or None
        - strategy: 'semantic' or 'keyword_fallback'

    Examples:
        "robaro meu cartao" → ('route', 0.45, 'semantic')  # Matches "bloquear cartao"
        "quero investir" → ('route', 0.52, 'semantic')     # Matches investment routes
        "iphone 15" → ('sku', 0.38, 'semantic')            # Clear product match
    '''
    global semantic_router

    # For very short queries, use keyword fallback (semantic matching unreliable)
    if len(query.strip()) < 4:
        return detect_intent_keyword(query), None, 'keyword_fallback'

    if semantic_router is None:
        # Fallback to keyword-based detection
        return detect_intent_keyword(query), None, 'keyword_fallback'

    try:
        # Get top match from semantic router
        route_match = semantic_router(query)

        if route_match.name is None:
            # No match - use mixed intent
            return "mixed", None, 'semantic'

        # Check confidence level
        distance = route_match.distance

        # High confidence - return single intent
        if distance < 0.55:
            return route_match.name, distance, 'semantic'

        # Medium confidence - check for ambiguity
        route_matches = semantic_router.route_many(query, max_k=2)

        if len(route_matches) >= 2:
            # Check if top 2 routes are very close (ambiguous)
            distance_diff = abs(route_matches[0].distance - route_matches[1].distance)

            if distance_diff < 0.1:
                # Ambiguous - mixed intent
                return "mixed", route_matches[0].distance, 'semantic'

        # Return best match
        return route_match.name, distance, 'semantic'
"""

def detect_intent_keyword(query: str) -> str:
    """
    Fallback keyword-based intent detection.
    Used when semantic router is unavailable.
    """
    query_lower = query.lower()

    # Route indicators
    route_keywords = ['pagar', 'transferir', 'pix', 'boleto', 'fatura', 'extrato',
                      'investir', 'emprestimo', 'seguro', 'recarga', 'limite',
                      'bloquear', 'cartao', 'roubo', 'perdi']

    # SKU indicators
    sku_keywords = ['comprar', 'produto', 'iphone', 'samsung', 'tv', 'notebook',
                    'celular', 'fone', 'relogio', 'tenis', 'camera']

    route_score = sum(1 for kw in route_keywords if kw in query_lower)
    sku_score = sum(1 for kw in sku_keywords if kw in query_lower)

    if route_score > sku_score:
        return 'route'
    elif sku_score > route_score:
        return 'sku'
    else:
        return 'mixed'

def search_taskbar(
    query: str,
    lang: str = "pt",
    country: str = "BR",
    limit: int = DEFAULT_LIMIT,
    user_ctx: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Main search function - 2-phase search (text → vector)

    Phase 1: Text search (exact + synonym + prefix)
    - Exact match with synonym expansion (FT.SYNUPDATE)
    - Prefix matching (query*)

    Phase 2: Vector search (only if Phase 1 < limit)
    - KNN semantic search

    This approach ensures:
    - Text matches ALWAYS come first
    - No "guessing" which type of match occurred
    - Simple, predictable ranking
    """
    start_time = time.time()
    tracking_id = f"search_{int(time.time() * 1000)}"

    # Prepare results container
    all_results = []
    seen_ids = set()

    # Search all indexes
    indexes = {
        'idx:routes': ('route', 1.0),
        'idx:skus': ('sku', 1.0),
        'idx:products': ('product', 1.0)
    }

    for idx_name, (doc_type, boost) in indexes.items():
        try:
            # ===== PHASE 1: TEXT SEARCH (Exact + Synonym + Prefix) =====
            # Query format: (query | query*)
            # - "query" (exact) → expands synonyms ✅
            # - "query*" (prefix) → does NOT expand synonyms, but matches prefixes ✅
            text_query = f"@lang:{{{lang}}} @country:{{{country}}} ({query} | {query}*)"

            text_result = redis_client.execute_command(
                'FT.SEARCH', idx_name, text_query,
                'LIMIT', '0', str(limit),
                'RETURN', '10', '$.id', '$.type', '$.title', '$.subtitle',
                '$.deep_link', '$.url', '$.icon', '$.category', '$.popularity', '$.price'
            )

            # Parse text search results
            if text_result[0] > 0:  # Has results
                for i in range(1, len(text_result), 2):
                    doc_key = text_result[i].decode('utf-8')
                    fields = text_result[i + 1]

                    # Parse fields
                    doc_data = {}
                    for j in range(0, len(fields), 2):
                        field_name = fields[j].decode('utf-8')
                        field_value = fields[j + 1].decode('utf-8') if fields[j + 1] else ''

                        # Parse JSON values
                        if field_value.startswith('['):
                            doc_data[field_name.replace('$.', '')] = json.loads(field_value)[0] if json.loads(field_value) else ''
                        else:
                            doc_data[field_name.replace('$.', '')] = field_value

                    doc_id = doc_data.get('id', '')
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)

                        # Text matches get high base score
                        base_score = 10.0  # Text matches are strong signals
                        popularity = float(doc_data.get('popularity', 50)) / 100.0
                        final_score = (base_score * boost) + (popularity * POPULARITY_WEIGHT)

                        all_results.append({
                            'type': doc_data.get('type', doc_type),
                            'id': doc_id,
                            'title': doc_data.get('title', ''),
                            'subtitle': doc_data.get('subtitle', ''),
                            'deep_link': doc_data.get('deep_link', doc_data.get('url', '')),
                            'icon': doc_data.get('icon', ''),
                            'category': doc_data.get('category', ''),
                            'score': final_score,
                            'price': doc_data.get('price'),
                            'highlights': [],
                            'match_type': 'text'  # We KNOW it's text match!
                        })

            # ===== PHASE 2: VECTOR SEARCH (only if text results < limit) =====
            # Only run vector search if we don't have enough text results
            if len(all_results) < limit:
                # Generate query embedding (lazy - only if needed)
                query_embedding = embed_function(query)
                query_vector_bytes = vector_to_bytes(query_embedding)

                # How many more results do we need?
                remaining = limit - len(all_results)
                vector_limit = remaining * 2  # Get 2x to have options

                vector_query = f"(@lang:{{{lang}}} @country:{{{country}}})=>[KNN {vector_limit} @embedding $vec AS vector_score]"

                vector_result = redis_client.execute_command(
                    'FT.SEARCH', idx_name, vector_query,
                    'PARAMS', '2', 'vec', query_vector_bytes,
                    'SORTBY', 'vector_score', 'ASC',
                    'LIMIT', '0', str(vector_limit),
                    'RETURN', '11', '$.id', '$.type', '$.title', '$.subtitle',
                    '$.deep_link', '$.url', '$.icon', '$.category', '$.popularity', '$.price', 'vector_score',
                    'DIALECT', '2'
                )

                # Parse vector search results
                if vector_result[0] > 0:
                    for i in range(1, len(vector_result), 2):
                        doc_key = vector_result[i].decode('utf-8')
                        fields = vector_result[i + 1]

                        # Parse fields
                        doc_data = {}
                        vector_score = None
                        for j in range(0, len(fields), 2):
                            field_name = fields[j].decode('utf-8')
                            field_value = fields[j + 1]

                            if field_name == 'vector_score':
                                vector_score = float(field_value.decode('utf-8'))
                            else:
                                field_value_str = field_value.decode('utf-8') if field_value else ''
                                # Parse JSON values
                                if field_value_str.startswith('['):
                                    doc_data[field_name.replace('$.', '')] = json.loads(field_value_str)[0] if json.loads(field_value_str) else ''
                                else:
                                    doc_data[field_name.replace('$.', '')] = field_value_str

                        doc_id = doc_data.get('id', '')
                        if doc_id and doc_id not in seen_ids:
                            seen_ids.add(doc_id)

                            # Vector matches get lower base score than text matches
                            # Convert distance to similarity: 1 - (distance / 2)
                            similarity = 1.0 - (vector_score / 2.0) if vector_score is not None else 0.5
                            base_score = similarity * 5.0  # Lower than text (10.0)
                            popularity = float(doc_data.get('popularity', 50)) / 100.0
                            final_score = (base_score * boost) + (popularity * POPULARITY_WEIGHT)

                            all_results.append({
                                'type': doc_data.get('type', doc_type),
                                'id': doc_id,
                                'title': doc_data.get('title', ''),
                                'subtitle': doc_data.get('subtitle', ''),
                                'deep_link': doc_data.get('deep_link', doc_data.get('url', '')),
                                'icon': doc_data.get('icon', ''),
                                'category': doc_data.get('category', ''),
                                'score': final_score,
                                'price': doc_data.get('price'),
                                'highlights': [],
                                'match_type': 'vector',  # We KNOW it's vector match!
                                'vector_distance': vector_score
                            })

        except Exception as e:
            print(f"Error searching {idx_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Sort by score
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # Limit results
    final_results = all_results[:limit]

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    return {
        'tracking_id': tracking_id,
        'latency_ms': latency_ms,
        'query': query,
        'total': len(final_results),
        'results': final_results
    }

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="Banco Inter Task Bar API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# STARTUP EVENT - Auto-seed if indexes don't exist
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize indexes and seed data if needed (non-destructive)"""
    try:
        # Check if indexes exist by trying to get info on one of them
        redis_client.execute_command('FT.INFO', 'idx:routes')
        print("✅ Indexes already exist - skipping seed")
        print("⚠️  If you updated JSONLs or code, run: curl -X POST http://localhost:8000/seed")
    except redis.exceptions.ResponseError:
        # Indexes don't exist - create and seed
        print("🌱 Indexes not found - creating and seeding data...")
        create_indexes()
        counts = seed_data()
        syn_count = setup_synonyms()
        ac_count = setup_autocomplete()
        print(f"✅ Seeded: {counts}")
        print(f"✅ Synonyms: {syn_count} groups")
        print(f"✅ Autocomplete: {ac_count} suggestions")
    except Exception as e:
        print(f"⚠️  Startup check failed: {e}")
        print("   You may need to run /seed endpoint manually")

# Pydantic Models
class SearchResponse(BaseModel):
    tracking_id: str
    latency_ms: int
    query: str
    total: int
    results: List[Dict[str, Any]]

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/seed")
async def seed_endpoint():
    """Load data from JSONL files into Redis"""
    create_indexes()
    counts = seed_data()
    syn_count = setup_synonyms()
    ac_count = setup_autocomplete()

    # DISABLED: Semantic router initialization (using parallel search instead)
    # router_initialized = initialize_semantic_router()

    return {
        "status": "success",
        "message": "Data seeded successfully with autocomplete and synonyms",
        "counts": counts,
        "synonyms": syn_count,
        "autocomplete_suggestions": ac_count
    }

@app.get("/autocomplete")
async def autocomplete_endpoint(
    q: str = Query(..., description="Autocomplete query"),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Autocomplete suggestions using FT.SUGGET.
    Fast, fuzzy matching for dropdown suggestions.
    """
    if len(q) < 2:
        return {
            "query": q,
            "suggestions": [],
            "total": 0
        }

    try:
        ac_key = "ac:taskbar"

        # Use FT.SUGGET with FUZZY for typo tolerance
        result = redis_client.execute_command(
            'FT.SUGGET', ac_key, q,
            'FUZZY',
            'WITHPAYLOADS',
            'MAX', str(limit)
        )

        # Parse results
        # Format: [suggestion1, payload1, suggestion2, payload2, ...]
        suggestions = []
        seen_ids = set()

        for i in range(0, len(result), 2):
            suggestion_text = result[i].decode('utf-8')
            payload = result[i + 1].decode('utf-8') if i + 1 < len(result) else None

            # Avoid duplicates
            if payload and payload not in seen_ids:
                seen_ids.add(payload)

                # Get document details
                doc_key = None
                if payload.startswith('route_'):
                    doc_key = f'route:{payload}'
                elif payload.startswith('sku_'):
                    doc_key = f'sku:{payload}'
                elif payload.startswith('prod_'):
                    doc_key = f'product:{payload}'

                if doc_key:
                    try:
                        doc_json = redis_client.execute_command('JSON.GET', doc_key)
                        if doc_json:
                            doc = json.loads(doc_json)
                            suggestions.append({
                                'text': suggestion_text,
                                'id': doc.get('id'),
                                'title': doc.get('title'),
                                'subtitle': doc.get('subtitle'),
                                'icon': doc.get('icon'),
                                'type': doc.get('type'),
                                'deep_link': doc.get('deep_link', doc.get('url'))
                            })
                    except:
                        pass

        return {
            "query": q,
            "suggestions": suggestions,
            "total": len(suggestions)
        }

    except Exception as e:
        print(f"Autocomplete error: {e}")
        return {
            "query": q,
            "suggestions": [],
            "total": 0
        }

@app.get("/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., description="Search query"),
    lang: str = Query("pt", description="Language code"),
    country: str = Query("BR", description="Country code"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=50)
):
    """Search across routes, SKUs, and products with hybrid search (text + vector)"""
    return search_taskbar(q, lang, country, limit)

@app.get("/health")
async def health():
    """Health check"""
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except:
        return {"status": "unhealthy", "redis": "disconnected"}

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Banco Inter Task Bar API...")
    print(f"📡 Server running at: http://localhost:8000")
    print(f"📚 API docs at: http://localhost:8000/docs")
    print(f"🔍 Open http://localhost:8000 in your browser")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

