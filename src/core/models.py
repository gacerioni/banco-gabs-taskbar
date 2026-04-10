"""
Pydantic Models for Banco Inter Taskbar
All API request/response models in one place
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


# ============================================================================
# SEARCH MODELS
# ============================================================================

class SearchResponse(BaseModel):
    """Legacy search response (backward compatible)"""
    tracking_id: str
    latency_ms: int
    query: str
    total: int
    results: List[Dict[str, Any]]


class UnifiedSearchResponse(BaseModel):
    """Unified response for both search and chat intents"""
    tracking_id: str
    latency_ms: float
    query: str
    language: str
    intent: str  # 'search' or 'chat'
    confidence: float
    
    # For search intent
    total: Optional[int] = None
    results: Optional[List[Dict[str, Any]]] = None
    
    # For chat intent
    chat_response: Optional[str] = None
    chat_provider: Optional[str] = None
    chat_model: Optional[str] = None


# ============================================================================
# ROUTING MODELS
# ============================================================================

class RoutingResult(BaseModel):
    """Result from semantic router"""
    language: str  # 'pt', 'en', 'es'
    intent: str    # 'search', 'chat'
    confidence: float  # 0.0 - 1.0


# ============================================================================
# CHAT MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request"""
    query: str
    language: Optional[str] = 'pt'
    use_openai: Optional[bool] = False


class ChatResponse(BaseModel):
    """Chat response"""
    type: str = "chat"
    query: str
    language: str
    response: str
    provider: str  # 'mock' or 'openai'
    model: str
    latency_ms: float


# ============================================================================
# SEED MODELS
# ============================================================================

class SeedResponse(BaseModel):
    """Response from seed endpoint"""
    status: str
    counts: Dict[str, int]
    message: str


# ============================================================================
# HEALTH MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    redis_connected: bool

