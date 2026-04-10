"""
Seed Endpoint
Database seeding endpoint
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time

from ...data import get_redis_client
from ...data.redis_indexes import create_all_indexes
from ...data.seed.seeder import seed_all
from ...data.synonyms import apply_synonyms_to_all
from ...search.autocomplete import setup_autocomplete
from ...routers.intent_router import force_reload_routers


router = APIRouter()


@router.post("/seed")
async def seed() -> Dict[str, Any]:
    """
    Seed database endpoint.
    
    Creates indexes, seeds data, applies synonyms, and sets up autocomplete.
    """
    try:
        redis_client = get_redis_client()
        start = time.time()
        
        # Create indexes
        print("🔨 Creating indexes...")
        indexes_created = create_all_indexes(redis_client)
        
        # Seed data
        print("🌱 Seeding data...")
        counts = seed_all(redis_client)
        
        # Apply synonyms
        print("📖 Applying synonyms...")
        syn_counts = apply_synonyms_to_all(redis_client)

        # Setup autocomplete
        print("🔍 Setting up autocomplete...")
        ac_count = setup_autocomplete(redis_client)

        # Force reload semantic routers
        print("🧠 Reloading semantic routers...")
        force_reload_routers()

        elapsed = time.time() - start
        
        return {
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "indexes_created": indexes_created,
            "documents_seeded": counts,
            "synonyms_applied": syn_counts,
            "autocomplete_suggestions": ac_count,
            "message": f"Seeded {sum(counts.values())} documents in {elapsed:.2f}s"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

