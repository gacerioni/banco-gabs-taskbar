"""
Chat handler for Redis Global Search Taskbar (concierge)
Chat intent: semantic guard (RedisVL) → static replies → OpenAI tools + Redis SKUs/cart or mock.
"""

from typing import Dict, Any, Optional
import time
import uuid

from ..core.config import config
from ..cart.store import get_cart_snapshot
from .concierge import run_concierge, run_concierge_mock
from .static_replies import try_static_chat_reply
from .stm_memory import get_concierge_chat_history
from .guard_replies import blocked_reply
from ..routers.guard_router import (
    classify_concierge_guard,
    guard_result_dict,
    empty_guard_dict,
)

# ============================================================================
# OPENAI CLIENT (lazy loaded) — optional for non-agent diagnostics
# ============================================================================

_openai_client = None


def get_openai_client():
    """Get or create OpenAI client (lazy loading)"""
    global _openai_client

    if _openai_client is None:
        if not config.OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY not set - concierge uses mock + Redis inventory")
            return None

        try:
            from openai import OpenAI

            _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("✅ OpenAI client initialized")
        except ImportError:
            print("⚠️  openai package not installed")
            return None
        except Exception as e:
            print(f"⚠️  Failed to initialize OpenAI client: {e}")
            return None

    return _openai_client


def _merge_guard(base: Dict[str, Any], guard_extra: Dict[str, Any]) -> Dict[str, Any]:
    out = {**base}
    out.update(guard_extra)
    return out


def handle_chat_query(
    query: str,
    language: str = "pt",
    use_openai: bool = True,
    redis_client=None,
    session_id: Optional[str] = None,
    include_tool_trace: bool = False,
) -> Dict[str, Any]:
    """
    Handle a chat (concierge) query.

    RedisVL semantic guard runs first (concierge paths only). Blocked routes
    return canned text without calling the LLM.

    When use_openai is True and OPENAI_API_KEY is set, runs tool-calling concierge
    (Redis hybrid SKU search + cart). Otherwise returns deterministic mock with
    live Redis inventory + cart snapshot.
    """
    start_time = time.time()
    sid = (session_id or "").strip() or str(uuid.uuid4())

    if redis_client is None:
        snap = {
            "session_id": sid,
            "items": [],
            "subtotal": 0.0,
            "currency": "BRL",
            "line_count": 0,
        }
        return _merge_guard(
            {
                "type": "chat",
                "query": query,
                "language": language,
                "response": "Redis client unavailable for concierge cart/search.",
                "provider": "error",
                "model": "none",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "cart": snap,
                "session_id": sid,
                "tool_trace": None,
            },
            empty_guard_dict(),
        )

    guard_extra: Dict[str, Any] = empty_guard_dict()
    if config.GUARD_ENABLED:
        gc = classify_concierge_guard(query.strip())
        guard_extra = guard_result_dict(gc)
        if gc.blocked:
            text = blocked_reply(gc.route, language)
            cart = get_cart_snapshot(redis_client, sid)
            try:
                stm_hist = get_concierge_chat_history(sid)
                stm_hist.add_user_message(query)
                stm_hist.add_ai_message(text)
            except Exception as e:
                print(f"⚠️  STM persist (guard block): {e}")
            return _merge_guard(
                {
                    "type": "chat",
                    "query": query,
                    "language": language,
                    "response": text,
                    "provider": "redisvl_guard",
                    "model": "semantic_router",
                    "latency_ms": round((time.time() - start_time) * 1000, 2),
                    "cart": cart,
                    "session_id": cart.get("session_id", sid),
                    "tool_trace": None,
                },
                guard_extra,
            )

    static_text = try_static_chat_reply(query.strip(), language)
    if static_text:
        cart = get_cart_snapshot(redis_client, sid)
        try:
            stm_hist = get_concierge_chat_history(sid)
            stm_hist.add_user_message(query)
            stm_hist.add_ai_message(static_text)
        except Exception as e:
            print(f"⚠️  STM persist (static reply): {e}")
        return _merge_guard(
            {
                "type": "chat",
                "query": query,
                "language": language,
                "response": static_text,
                "provider": "static_reply",
                "model": "none",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "cart": cart,
                "session_id": cart.get("session_id", sid),
                "tool_trace": None,
            },
            guard_extra,
        )

    use_concierge = bool(use_openai and config.OPENAI_API_KEY)
    stm_persisted_in_run_concierge = False

    try:
        if use_concierge:
            out = run_concierge(
                redis_client,
                query,
                sid,
                language=language,
                include_tool_trace=include_tool_trace,
            )
            stm_persisted_in_run_concierge = True
        else:
            out = run_concierge_mock(redis_client, query, sid, language=language)
    except Exception as e:
        print(f"⚠️  Concierge error: {e}")
        out = run_concierge_mock(redis_client, query, sid, language=language)
        out["response"] = (
            f"{out['response']}\n\n_(Falha no agente: {e!s}. Exibindo modo demonstração.)_"
        )
        stm_persisted_in_run_concierge = False

    if not stm_persisted_in_run_concierge and out.get("response"):
        try:
            stm_hist = get_concierge_chat_history(sid)
            stm_hist.add_user_message(query)
            stm_hist.add_ai_message(out["response"])
        except Exception as e:
            print(f"⚠️  STM persist (mock concierge): {e}")

    cart = out.get("cart") or {}
    if "session_id" not in cart:
        cart = {**cart, "session_id": sid}

    latency_ms = out.get("latency_ms")
    if latency_ms is None:
        latency_ms = round((time.time() - start_time) * 1000, 2)

    return _merge_guard(
        {
            "type": "chat",
            "query": query,
            "language": language,
            "response": out["response"],
            "provider": out.get("provider", "mock"),
            "model": out.get("model", "none"),
            "latency_ms": latency_ms,
            "cart": cart,
            "session_id": cart.get("session_id", sid),
            "tool_trace": out.get("tool_trace"),
        },
        guard_extra,
    )
