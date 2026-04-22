"""
Concierge chat API — sempre modo conversa (sem roteador search/chat da barra).
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ...data import get_redis_client
from ...chat import handle_chat_query
from ...chat.stm_memory import list_concierge_stm_messages
from ...cart.store import get_cart_snapshot
from ...core.config import config
from ...routers import detect_language

router = APIRouter()


def _resolve_chat_language(message: str, explicit: Optional[str]) -> str:
    """
    Use explicit pt/en/es when the client sends it; otherwise detect from the message
    (same detector as the taskbar) so EN prompts get EN concierge replies.
    """
    raw = (explicit or "").strip().lower()[:8]
    if raw in ("", "auto", "detect"):
        return detect_language(message.strip())
    if raw in ("pt", "en", "es"):
        return raw
    return detect_language(message.strip())


class ConciergeChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None
    language: Optional[str] = Field(
        default=None,
        max_length=8,
        description="pt, en, or es. Omit, null, or 'auto' to detect from the message text.",
    )


class ConciergeChatResponse(BaseModel):
    session_id: str
    language: str
    reply: str
    cart: Dict[str, Any]
    provider: str
    model: str
    latency_ms: float
    tool_trace: Optional[List[Dict[str, Any]]] = None
    # RedisVL semantic guard (concierge only)
    guard_route: Optional[str] = None
    guard_confidence: Optional[float] = None
    guard_distance: Optional[float] = None
    guard_second_route: Optional[str] = None
    guard_second_confidence: Optional[float] = None
    guard_margin: Optional[float] = None
    guard_latency_ms: Optional[float] = None
    guard_blocked: Optional[bool] = None


class ConciergeHistoryResponse(BaseModel):
    """STM messages from Redis (LangChain) for rehydrating the concierge UI."""

    session_id: str
    messages: List[Dict[str, str]]
    cart: Dict[str, Any]


@router.get("/api/concierge/history", response_model=ConciergeHistoryResponse)
async def concierge_history(
    session_id: str = Query(..., min_length=4, max_length=80, description="Same session_id as chat/cart"),
) -> ConciergeHistoryResponse:
    """
    Load conversation turns stored in Redis for this session so the browser can
    repaint the thread after refresh (STM is server-side only).
    """
    redis_client = get_redis_client()
    sid = session_id.strip()
    messages = list_concierge_stm_messages(sid, limit=100)
    cart = get_cart_snapshot(redis_client, sid)
    return ConciergeHistoryResponse(session_id=sid, messages=messages, cart=cart)


@router.post("/api/concierge/chat", response_model=ConciergeChatResponse)
async def concierge_chat(body: ConciergeChatRequest) -> ConciergeChatResponse:
    """
    Uma mensagem do painel flutuante → concierge (OpenAI + tools ou mock) + carrinho Redis.
    """
    redis_client = get_redis_client()
    sid = (body.session_id or "").strip() or str(uuid.uuid4())

    start = time.time()
    lang = _resolve_chat_language(body.message, body.language)
    out = handle_chat_query(
        query=body.message.strip(),
        language=lang,
        use_openai=True,
        redis_client=redis_client,
        session_id=sid,
        include_tool_trace=config.DEBUG,
    )
    elapsed = (time.time() - start) * 1000

    cart = out.get("cart") or {}
    if "session_id" not in cart:
        cart = {**cart, "session_id": out.get("session_id", sid)}

    return ConciergeChatResponse(
        session_id=out.get("session_id", sid),
        language=lang,
        reply=out.get("response", ""),
        cart=cart,
        provider=out.get("provider", "mock"),
        model=out.get("model", "none"),
        latency_ms=round(elapsed, 2),
        tool_trace=out.get("tool_trace"),
        guard_route=out.get("guard_route"),
        guard_confidence=out.get("guard_confidence"),
        guard_distance=out.get("guard_distance"),
        guard_second_route=out.get("guard_second_route"),
        guard_second_confidence=out.get("guard_second_confidence"),
        guard_margin=out.get("guard_margin"),
        guard_latency_ms=out.get("guard_latency_ms"),
        guard_blocked=out.get("guard_blocked"),
    )
