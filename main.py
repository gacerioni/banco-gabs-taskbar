"""
Banco Inter Taskbar - Main Entry Point
Clean, modular architecture with Redis 8.6 HYBRID search

All business logic is in src/ modules
"""

import os
from contextlib import asynccontextmanager

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import config
from src.data import get_redis_client, close_redis_client
from src.data.redis_indexes import indexes_exist_all, create_all_indexes
from src.data.seed.seeder import seed_all
from src.data.synonyms import apply_synonyms_to_all
from src.search.autocomplete import setup_autocomplete
from src.api import health_router, seed_router, search_router, autocomplete_router, feedback_router
from src.api.endpoints.admin import router as admin_router


# ============================================================================
# LIFESPAN (Startup/Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    
    # STARTUP
    print("=" * 80)
    print("🏦 Banco Inter Taskbar - Starting...")
    print("=" * 80)
    print(f"📍 Redis: {config.REDIS_URL[:40]}...")
    print(f"🤖 Embedding Model: {config.EMBEDDING_MODEL}")
    print(f"📏 Dimensions: {config.EMBEDDING_DIM}")
    print(f"⚖️  Hybrid Weights: FTS={config.FTS_WEIGHT} / VSS={config.VSS_WEIGHT}")
    print("=" * 80)
    
    # Connect to Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        db_size = redis_client.dbsize()
        print(f"✅ Redis connected ({db_size} keys)")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        raise
    
    # Auto-seed if indexes don't exist
    if not indexes_exist_all(redis_client):
        print("\n🌱 Indexes not found - creating and seeding...")
        try:
            create_all_indexes(redis_client)
            seed_all(redis_client)
            apply_synonyms_to_all(redis_client)
            setup_autocomplete(redis_client)
            print("✅ Auto-seed complete")
        except Exception as e:
            print(f"❌ Auto-seed failed: {e}")
            # Don't raise - let app start anyway
    
    print("=" * 80)
    print("🚀 Server ready!")
    print("=" * 80)
    
    yield
    
    # SHUTDOWN
    print("\n👋 Shutting down...")
    close_redis_client()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Banco Inter Taskbar",
    description="Semantic search with Redis 8.6 HYBRID scoring (Customer 360)",
    version="2.0.0-refactored",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ROUTES
# ============================================================================

# Include API routers
app.include_router(health_router, tags=["Health"])
app.include_router(seed_router, tags=["Admin"])
app.include_router(search_router, tags=["Search"])
app.include_router(autocomplete_router, tags=["Search"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(feedback_router, tags=["Feedback"])


# Root endpoint - serve frontend
@app.get("/", include_in_schema=False)
async def root():
    """Serve frontend"""
    return FileResponse("static/index.html")


@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    """Serve admin dashboard"""
    return FileResponse("static/admin.html")


@app.get("/admin/routes", include_in_schema=False)
async def admin_routes():
    """Serve routes manager"""
    return FileResponse("static/admin-routes.html")


@app.get("/admin/products", include_in_schema=False)
async def admin_products():
    """Serve products manager"""
    return FileResponse("static/admin-products.html")


@app.get("/admin/skus", include_in_schema=False)
async def admin_skus():
    """Serve SKUs manager"""
    return FileResponse("static/admin-skus.html")


@app.get("/admin/router", include_in_schema=False)
async def admin_router():
    """Serve router examples manager"""
    return FileResponse("static/admin-router.html")


# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

