"""
Database Seeder
Populates Redis from JSONL seed files
"""

import redis
import json
from typing import Dict, List
from pathlib import Path

from .loader import load_routes, load_products, load_skus
from ..models import route_schema, product_schema, sku_schema
from ...search.vectorizer import embed_texts


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================

def seed_routes(redis_client: redis.Redis) -> int:
    """
    Seed routes from routes.jsonl
    
    Returns:
        Number of routes inserted
    """
    routes = load_routes()
    
    if not routes:
        print("⚠️  No routes to seed")
        return 0
    
    # Generate embeddings for all routes
    texts_to_embed = []
    for route in routes:
        # Combine title + subtitle + description for embedding
        text = f"{route.get('title', '')} {route.get('subtitle', '')} {route.get('description', '')}"
        texts_to_embed.append(text.strip())
    
    print(f"🔢 Generating embeddings for {len(routes)} routes...")
    embeddings = embed_texts(texts_to_embed)
    
    # Insert into Redis
    count = 0
    for i, route in enumerate(routes):
        route_id = route.get('id', f'route_{i}')
        key = f"{route_schema.INDEX_PREFIX}{route_id}"
        
        # Add embedding to route data
        route['embedding'] = embeddings[i]
        
        # Store as JSON
        redis_client.json().set(key, '$', route)
        count += 1
    
    print(f"✅ Seeded {count} routes")
    return count


def seed_products(redis_client: redis.Redis) -> int:
    """
    Seed products from products.jsonl
    
    Returns:
        Number of products inserted
    """
    products = load_products()
    
    if not products:
        print("⚠️  No products to seed")
        return 0
    
    # Generate embeddings
    texts_to_embed = []
    for product in products:
        text = f"{product.get('title', '')} {product.get('subtitle', '')} {product.get('description', '')}"
        texts_to_embed.append(text.strip())
    
    print(f"🔢 Generating embeddings for {len(products)} products...")
    embeddings = embed_texts(texts_to_embed)
    
    # Insert into Redis
    count = 0
    for i, product in enumerate(products):
        product_id = product.get('id', f'product_{i}')
        key = f"{product_schema.INDEX_PREFIX}{product_id}"
        
        product['embedding'] = embeddings[i]
        redis_client.json().set(key, '$', product)
        count += 1
    
    print(f"✅ Seeded {count} products")
    return count


def seed_skus(redis_client: redis.Redis) -> int:
    """
    Seed SKUs from skus.jsonl
    
    Returns:
        Number of SKUs inserted
    """
    skus = load_skus()
    
    if not skus:
        print("⚠️  No SKUs to seed")
        return 0
    
    # Generate embeddings
    texts_to_embed = []
    for sku in skus:
        text = f"{sku.get('title', '')} {sku.get('brand', '')} {sku.get('description', '')}"
        texts_to_embed.append(text.strip())
    
    print(f"🔢 Generating embeddings for {len(skus)} SKUs...")
    embeddings = embed_texts(texts_to_embed)
    
    # Insert into Redis
    count = 0
    for i, sku in enumerate(skus):
        sku_id = sku.get('id', f'sku_{i}')
        key = f"{sku_schema.INDEX_PREFIX}{sku_id}"
        
        sku['embedding'] = embeddings[i]
        redis_client.json().set(key, '$', sku)
        count += 1
    
    print(f"✅ Seeded {count} SKUs")
    return count


def seed_all(redis_client: redis.Redis) -> Dict[str, int]:
    """
    Seed all data from JSONL files.
    
    Returns:
        Dict with counts: {'routes': N, 'products': M, 'skus': K}
    """
    print("=" * 80)
    print("🌱 Seeding Database from JSONL")
    print("=" * 80)
    
    import time
    start = time.time()
    
    counts = {
        'routes': seed_routes(redis_client),
        'products': seed_products(redis_client),
        'skus': seed_skus(redis_client),
    }
    
    elapsed = time.time() - start
    total = sum(counts.values())
    
    print("=" * 80)
    print(f"✅ Seeded {total} total documents in {elapsed:.2f}s")
    print(f"   Routes: {counts['routes']}")
    print(f"   Products: {counts['products']}")
    print(f"   SKUs: {counts['skus']}")
    print("=" * 80)
    
    return counts

