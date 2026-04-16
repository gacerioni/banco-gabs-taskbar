"""
Admin API Endpoints - CRUD for routes, products, SKUs
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
import uuid
import json

from ...data import get_redis_client
from ...search.vectorizer import embed_text
from ...search.query_cache import invalidate_search_cache

router = APIRouter(prefix="/admin/api", tags=["admin"])


# ============================================================================
# ROUTES CRUD
# ============================================================================

@router.get("/routes")
async def list_routes(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """List all routes with pagination"""
    redis_client = get_redis_client()

    # Get all route keys
    keys = redis_client.keys("route:*")
    total = len(keys)

    # Paginate
    paginated_keys = keys[offset:offset + limit]

    routes = []
    for key in paginated_keys:
        doc = redis_client.json().get(key)
        if doc:
            doc.pop('embedding', None)  # Remove large embedding
            routes.append(doc)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": routes
    }


@router.get("/routes/{route_id}")
async def get_route(route_id: str) -> Dict[str, Any]:
    """Get single route by ID"""
    redis_client = get_redis_client()

    key = f"route:{route_id}"
    doc = redis_client.json().get(key)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    doc.pop('embedding', None)
    return doc


@router.post("/routes")
async def create_route(route: Dict[str, Any]) -> Dict[str, Any]:
    """Create new route with auto-embedding"""
    redis_client = get_redis_client()

    # Generate ID if not provided
    if 'id' not in route:
        route['id'] = f"route_{uuid.uuid4().hex[:12]}"

    # Ensure type
    route['type'] = 'route'

    # Generate embedding
    text_to_embed = f"{route.get('title', '')} {route.get('subtitle', '')} {route.get('description', '')} {route.get('keywords', '')} {route.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    route['embedding'] = embedding

    # Save to Redis
    key = f"route:{route['id']}"
    redis_client.json().set(key, '$', route)

    # 1. Instantly update Autocomplete
    title = route.get('title', '').strip()
    if title:
        try:
            score = route.get('popularity', 1.0)
            payload = f"route:{route['id']}"
            redis_client.execute_command("FT.SUGADD", "ac:global_search", title, score, "PAYLOAD", payload)
        except Exception as e:
            print(f"⚠️ Error adding to autocomplete: {e}")

    # 2. Append to JSONL seed file so it persists
    import json
    try:
        route_copy = route.copy()
        route_copy.pop('embedding', None) # Don't save large embeddings to JSONL
        with open('src/data/seed/routes.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(route_copy, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"⚠️ Error saving to JSONL: {e}")

    invalidate_search_cache(redis_client)
    print(f"✅ Created route: {route['id']}")

    route.pop('embedding', None)
    return route


@router.put("/routes/{route_id}")
async def update_route(route_id: str, route: Dict[str, Any]) -> Dict[str, Any]:
    """Update route and reprocess embedding"""
    redis_client = get_redis_client()

    key = f"route:{route_id}"

    # Check if exists
    existing = redis_client.json().get(key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    # Ensure ID and type
    route['id'] = route_id
    route['type'] = 'route'

    # Regenerate embedding
    text_to_embed = f"{route.get('title', '')} {route.get('subtitle', '')} {route.get('description', '')} {route.get('keywords', '')} {route.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    route['embedding'] = embedding

    # Update in Redis
    redis_client.json().set(key, '$', route)

    invalidate_search_cache(redis_client)
    print(f"✅ Updated route: {route_id}")

    route.pop('embedding', None)
    return route


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str) -> Dict[str, Any]:
    """Delete route"""
    redis_client = get_redis_client()

    key = f"route:{route_id}"

    # Check if exists
    if not redis_client.exists(key):
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    # Delete
    redis_client.delete(key)

    invalidate_search_cache(redis_client)
    print(f"🗑️  Deleted route: {route_id}")

    return {"message": f"Route {route_id} deleted successfully"}


@router.post("/routes/{route_id}/reprocess")
async def reprocess_route_embedding(route_id: str) -> Dict[str, Any]:
    """Reprocess embedding for a route"""
    redis_client = get_redis_client()

    key = f"route:{route_id}"
    doc = redis_client.json().get(key)

    if not doc:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")

    # Regenerate embedding from document fields
    text_to_embed = f"{doc.get('title', '')} {doc.get('subtitle', '')} {doc.get('description', '')} {doc.get('keywords', '')} {doc.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    doc['embedding'] = embedding

    # Update in Redis
    redis_client.json().set(key, '$', doc)

    invalidate_search_cache(redis_client)
    print(f"Reprocessed embedding for route: {route_id}")

    return {"message": f"Embedding reprocessed for route {route_id}"}



# ============================================================================
# PRODUCTS CRUD
# ============================================================================

@router.get("/products")
async def list_products(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """List all products"""
    redis_client = get_redis_client()
    keys = redis_client.keys("product:*")
    total = len(keys)
    paginated_keys = keys[offset:offset + limit]

    products = []
    for key in paginated_keys:
        doc = redis_client.json().get(key)
        if doc:
            doc.pop('embedding', None)
            products.append(doc)

    return {"total": total, "limit": limit, "offset": offset, "items": products}


@router.get("/products/{product_id}")
async def get_product(product_id: str) -> Dict[str, Any]:
    """Get single product"""
    redis_client = get_redis_client()
    key = f"product:{product_id}"
    doc = redis_client.json().get(key)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    doc.pop('embedding', None)
    return doc


@router.post("/products")
async def create_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """Create new product"""
    redis_client = get_redis_client()
    if 'id' not in product:
        product['id'] = f"product_{uuid.uuid4().hex[:12]}"
    product['type'] = 'product'

    text_to_embed = f"{product.get('title', '')} {product.get('subtitle', '')} {product.get('description', '')} {product.get('benefits', '')} {product.get('keywords', '')} {product.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    product['embedding'] = embedding

    key = f"product:{product['id']}"
    redis_client.json().set(key, '$', product)

    # 1. Instantly update Autocomplete
    title = product.get('title', '').strip()
    if title:
        try:
            score = product.get('popularity', 1.0)
            payload = f"product:{product['id']}"
            redis_client.execute_command("FT.SUGADD", "ac:global_search", title, score, "PAYLOAD", payload)
        except Exception as e:
            print(f"⚠️ Error adding to autocomplete: {e}")

    # 2. Append to JSONL seed file so it persists
    import json
    try:
        product_copy = product.copy()
        product_copy.pop('embedding', None) # Don't save large embeddings to JSONL
        with open('src/data/seed/products.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(product_copy, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"⚠️ Error saving to JSONL: {e}")

    invalidate_search_cache(redis_client)
    print(f"✅ Created product: {product['id']}")

    product.pop('embedding', None)
    return product


@router.put("/products/{product_id}")
async def update_product(product_id: str, product: Dict[str, Any]) -> Dict[str, Any]:
    """Update product"""
    redis_client = get_redis_client()
    key = f"product:{product_id}"

    if not redis_client.json().get(key):
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    product['id'] = product_id
    product['type'] = 'product'

    text_to_embed = f"{product.get('title', '')} {product.get('subtitle', '')} {product.get('description', '')} {product.get('benefits', '')} {product.get('keywords', '')} {product.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    product['embedding'] = embedding

    redis_client.json().set(key, '$', product)

    invalidate_search_cache(redis_client)
    print(f"✅ Updated product: {product_id}")

    product.pop('embedding', None)
    return product


@router.delete("/products/{product_id}")
async def delete_product(product_id: str) -> Dict[str, Any]:
    """Delete product"""
    redis_client = get_redis_client()
    key = f"product:{product_id}"
    if not redis_client.exists(key):
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    redis_client.delete(key)

    invalidate_search_cache(redis_client)
    print(f"🗑️  Deleted product: {product_id}")
    return {"message": f"Product {product_id} deleted successfully"}


# ============================================================================
# SKUS CRUD
# ============================================================================

@router.get("/skus")
async def list_skus(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """List all SKUs"""
    redis_client = get_redis_client()
    keys = redis_client.keys("sku:*")
    total = len(keys)
    paginated_keys = keys[offset:offset + limit]

    skus = []
    for key in paginated_keys:
        doc = redis_client.json().get(key)
        if doc:
            doc.pop('embedding', None)
            skus.append(doc)

    return {"total": total, "limit": limit, "offset": offset, "items": skus}


@router.get("/skus/{sku_id}")
async def get_sku(sku_id: str) -> Dict[str, Any]:
    """Get single SKU"""
    redis_client = get_redis_client()
    key = f"sku:{sku_id}"
    doc = redis_client.json().get(key)
    if not doc:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    doc.pop('embedding', None)
    return doc


@router.post("/skus")
async def create_sku(sku: Dict[str, Any]) -> Dict[str, Any]:
    """Create new SKU"""
    redis_client = get_redis_client()
    if 'id' not in sku:
        sku['id'] = f"sku_{uuid.uuid4().hex[:12]}"
    sku['type'] = 'sku'

    text_to_embed = f"{sku.get('title', '')} {sku.get('brand', '')} {sku.get('description', '')} {sku.get('keywords', '')} {sku.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    sku['embedding'] = embedding

    key = f"sku:{sku['id']}"
    redis_client.json().set(key, '$', sku)

    # 1. Instantly update Autocomplete
    title = sku.get('title', '').strip()
    if title:
        try:
            score = sku.get('popularity', 1.0)
            payload = f"sku:{sku['id']}"
            redis_client.execute_command("FT.SUGADD", "ac:global_search", title, score, "PAYLOAD", payload)
        except Exception as e:
            print(f"⚠️ Error adding to autocomplete: {e}")

    # 2. Append to JSONL seed file so it persists
    import json
    try:
        sku_copy = sku.copy()
        sku_copy.pop('embedding', None) # Don't save large embeddings to JSONL
        with open('src/data/seed/skus.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(sku_copy, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"⚠️ Error saving to JSONL: {e}")

    invalidate_search_cache(redis_client)
    print(f"✅ Created SKU: {sku['id']}")

    sku.pop('embedding', None)
    return sku


@router.put("/skus/{sku_id}")
async def update_sku(sku_id: str, sku: Dict[str, Any]) -> Dict[str, Any]:
    """Update SKU"""
    redis_client = get_redis_client()
    key = f"sku:{sku_id}"

    if not redis_client.json().get(key):
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")

    sku['id'] = sku_id
    sku['type'] = 'sku'

    text_to_embed = f"{sku.get('title', '')} {sku.get('brand', '')} {sku.get('description', '')} {sku.get('keywords', '')} {sku.get('aliases', '')}"
    embedding = embed_text(text_to_embed)
    sku['embedding'] = embedding

    redis_client.json().set(key, '$', sku)

    # 1. Instantly update Autocomplete
    title = sku.get('title', '').strip()
    if title:
        try:
            score = sku.get('popularity', 1.0)
            payload = f"sku:{sku['id']}"
            redis_client.execute_command("FT.SUGADD", "ac:global_search", title, score, "PAYLOAD", payload)
        except Exception as e:
            print(f"⚠️ Error adding to autocomplete: {e}")

    # 2. Append to JSONL seed file so it persists
    import json
    try:
        sku_copy = sku.copy()
        sku_copy.pop('embedding', None) # Don't save large embeddings to JSONL
        with open('src/data/seed/skus.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(sku_copy, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"⚠️ Error saving to JSONL: {e}")

    invalidate_search_cache(redis_client)
    print(f"✅ Updated SKU: {sku_id}")

    sku.pop('embedding', None)
    return sku


@router.delete("/skus/{sku_id}")
async def delete_sku(sku_id: str) -> Dict[str, Any]:
    """Delete SKU"""
    redis_client = get_redis_client()
    key = f"sku:{sku_id}"
    if not redis_client.exists(key):
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    redis_client.delete(key)

    invalidate_search_cache(redis_client)
    print(f"Deleted SKU: {sku_id}")

    return {"message": f"SKU {sku_id} deleted successfully"}


# ============================================================================
# ROUTER EXAMPLES MANAGEMENT
# ============================================================================

@router.get("/router-examples")
async def list_router_examples(
    language: str = Query(None, description="Filter by language (pt, en, es)"),
    intent: str = Query(None, description="Filter by intent (search, chat)")
) -> Dict[str, Any]:
    """List all router examples with optional filters"""
    import os
    import json

    examples = []
    base_path = "src/data/seed/router_examples"

    # Get all JSONL files
    files = []
    if language and intent:
        files = [f"{language}_{intent}.jsonl"]
    elif language:
        files = [f"{language}_search.jsonl", f"{language}_chat.jsonl"]
    elif intent:
        files = [f"pt_{intent}.jsonl", f"en_{intent}.jsonl", f"es_{intent}.jsonl"]
    else:
        files = os.listdir(base_path)

    for filename in files:
        if not filename.endswith('.jsonl'):
            continue

        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    example = json.loads(line.strip())
                    example['_id'] = f"{filename}:{line_num}"  # Unique ID
                    example['_file'] = filename
                    examples.append(example)
                except:
                    pass

    return {
        "total": len(examples),
        "items": examples
    }


@router.post("/router-examples")
async def create_router_example(example: Dict[str, Any]) -> Dict[str, Any]:
    """Add new router example dynamically (HOT RELOAD - no restart needed!)"""
    import json

    language = example.get('language', 'pt')
    intent = example.get('intent', 'search')
    example_text = example.get('example', '')

    if not example_text:
        raise HTTPException(status_code=400, detail="Example text is required")

    # 1. Save to JSONL file (persistence)
    filename = f"src/data/seed/router_examples/{language}_{intent}.jsonl"
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"✅ Saved to file: {example_text} ({language}/{intent})")

    # 2. Add to live router (HOT RELOAD!)
    try:
        from src.routers.intent_router import get_semantic_router

        # Get the router for this language
        semantic_router = get_semantic_router(language)

        # Add example to the route dynamically
        semantic_router.add_route_references(
            route_name=intent,
            references=[example_text]
        )

        print(f"🔥 HOT RELOAD: Added '{example_text}' to {intent} route ({language})")

        return {
            "message": "Example added successfully (HOT RELOAD - no restart needed!)",
            "example": example,
            "language": language,
            "intent": intent,
            "note": f"Router immediately updated - '{example_text}' will now route to {intent.upper()}"
        }

    except Exception as e:
        print(f"⚠️  Error adding to router: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add example to router: {str(e)}")


@router.delete("/router-examples/{example_id}")
async def delete_router_example(example_id: str) -> Dict[str, Any]:
    """Delete router example dynamically (HOT RELOAD - no restart needed!)"""
    import json

    # example_id format: "pt_search.jsonl:5"
    filename, line_num = example_id.split(':')
    line_num = int(line_num)

    # Extract language and intent from filename (e.g., "pt_search.jsonl" -> "pt", "search")
    parts = filename.replace('.jsonl', '').split('_')
    language = parts[0]
    intent = parts[1]

    filepath = f"src/data/seed/router_examples/{filename}"

    # Read all lines to get the example text
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if line_num > len(lines) or line_num < 1:
        raise HTTPException(status_code=404, detail=f"Line {line_num} not found in {filename}")

    # Parse the line to get example text
    try:
        example_data = json.loads(lines[line_num - 1])
        example_text = example_data.get('example', '')
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON at line {line_num}")

    # Remove line from file
    del lines[line_num - 1]

    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"🗑️  Deleted from file: {example_text} ({language}/{intent})")

    # Force-rebuild the router index so the deleted example is removed immediately
    # (overwrite=True re-embeds all remaining examples from the updated JSONL file)
    try:
        from src.routers.intent_router import get_semantic_router

        get_semantic_router(language, overwrite=True)
        print(f"🔄 Router for '{language}' rebuilt with updated examples")

        return {
            "message": f"Example deleted and router rebuilt immediately",
            "example": example_text,
            "language": language,
            "intent": intent,
            "note": f"Router for {language.upper()} is already using updated examples"
        }

    except Exception as e:
        print(f"⚠️  Error clearing router cache: {e}")
        # Not critical - file was updated successfully
        return {
            "message": f"Example deleted from file (router will reload on restart)",
            "example": example_text
        }


@router.post("/router-examples/retrain")
async def retrain_router() -> Dict[str, Any]:
    """Retrain router (requires server restart)"""
    return {
        "message": "Router retraining requires server restart",
        "instruction": "Please restart the server to reload router examples"
    }

