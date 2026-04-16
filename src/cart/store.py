"""
Shopping cart stored in Redis (Hash per session).
Key: demo:cart:{session_id} — fields: sku_id -> JSON line payload.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

import redis

from ..core.config import config

CART_KEY_PREFIX = "demo:cart:"
CART_TTL_SECONDS = int(getattr(config, "CART_TTL_SECONDS", 604800))


def _cart_key(session_id: str) -> str:
    return f"{CART_KEY_PREFIX}{session_id}"


def _ensure_session(session_id: Optional[str]) -> str:
    if session_id and str(session_id).strip():
        return str(session_id).strip()
    return str(uuid.uuid4())


def get_cart_snapshot(redis_client: redis.Redis, session_id: str) -> Dict[str, Any]:
    """Return cart as API-friendly dict."""
    sid = _ensure_session(session_id)
    key = _cart_key(sid)
    raw = redis_client.hgetall(key)
    items: List[Dict[str, Any]] = []
    subtotal = 0.0

    for sku_id, payload in raw.items():
        if isinstance(sku_id, bytes):
            sku_id = sku_id.decode("utf-8", errors="replace")
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        try:
            line = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            continue
        qty = int(line.get("qty", 1))
        unit = float(line.get("unit_price", 0) or 0)
        line_total = round(unit * qty, 2)
        subtotal += line_total
        items.append(
            {
                "sku_id": sku_id,
                "title": line.get("title", sku_id),
                "qty": qty,
                "unit_price": unit,
                "line_total": line_total,
                "in_stock_at_add": line.get("in_stock_at_add"),
            }
        )

    items.sort(key=lambda x: x["sku_id"])
    return {
        "session_id": sid,
        "items": items,
        "subtotal": round(subtotal, 2),
        "currency": "BRL",
        "line_count": len(items),
    }


def add_line(
    redis_client: redis.Redis,
    session_id: str,
    sku_id: str,
    qty: int,
    title: str,
    unit_price: float,
    in_stock: Optional[bool] = None,
) -> Dict[str, Any]:
    """Add or merge a line (increments qty if sku already present)."""
    sid = _ensure_session(session_id)
    if qty < 1:
        qty = 1
    key = _cart_key(sid)
    field = sku_id.strip()
    existing = redis_client.hget(key, field)
    prev_qty = 0
    if existing:
        try:
            data = json.loads(existing)
            prev_qty = int(data.get("qty", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            prev_qty = 0
    new_qty = prev_qty + qty
    payload = {
        "title": title,
        "unit_price": float(unit_price),
        "qty": new_qty,
        "in_stock_at_add": in_stock,
    }
    redis_client.hset(key, field, json.dumps(payload, ensure_ascii=False))
    redis_client.expire(key, CART_TTL_SECONDS)
    return get_cart_snapshot(redis_client, sid)


def set_line_quantity(
    redis_client: redis.Redis, session_id: str, sku_id: str, qty: int
) -> Dict[str, Any]:
    """Set absolute quantity; removes line if qty < 1."""
    sid = _ensure_session(session_id)
    key = _cart_key(sid)
    field = sku_id.strip()
    if qty < 1:
        redis_client.hdel(key, field)
        redis_client.expire(key, CART_TTL_SECONDS)
        return get_cart_snapshot(redis_client, sid)

    existing = redis_client.hget(key, field)
    if not existing:
        return get_cart_snapshot(redis_client, sid)
    if isinstance(existing, bytes):
        existing = existing.decode("utf-8", errors="replace")
    try:
        data = json.loads(existing)
    except (json.JSONDecodeError, TypeError):
        return get_cart_snapshot(redis_client, sid)
    data["qty"] = int(qty)
    redis_client.hset(key, field, json.dumps(data, ensure_ascii=False))
    redis_client.expire(key, CART_TTL_SECONDS)
    return get_cart_snapshot(redis_client, sid)


def remove_line(redis_client: redis.Redis, session_id: str, sku_id: str) -> Dict[str, Any]:
    sid = _ensure_session(session_id)
    key = _cart_key(sid)
    redis_client.hdel(key, sku_id.strip())
    redis_client.expire(key, CART_TTL_SECONDS)
    return get_cart_snapshot(redis_client, sid)


def clear_cart(redis_client: redis.Redis, session_id: str) -> Dict[str, Any]:
    sid = _ensure_session(session_id)
    redis_client.delete(_cart_key(sid))
    return get_cart_snapshot(redis_client, sid)


def fetch_sku_doc(redis_client: redis.Redis, sku_id: str) -> Optional[Dict[str, Any]]:
    """Load SKU JSON from Redis (sku:{id})."""
    clean = sku_id.strip()
    if not clean.startswith("sku:"):
        clean_key = f"sku:{clean}"
    else:
        clean_key = clean
    doc = redis_client.json().get(clean_key)
    if not doc or not isinstance(doc, dict):
        return None
    if doc.get("type") != "sku":
        return None
    return doc
