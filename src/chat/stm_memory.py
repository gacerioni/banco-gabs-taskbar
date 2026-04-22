"""
Short-term memory for concierge: LangChain RedisChatMessageHistory (Redis + index).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_redis import RedisChatMessageHistory

from ..core.config import config


def _message_content_to_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        try:
            return json.dumps(content, ensure_ascii=False)[:8000]
        except (TypeError, ValueError):
            return str(content)[:8000]
    return str(content)[:8000] if content is not None else ""


def list_concierge_stm_messages(session_id: str, limit: int = 100) -> List[Dict[str, str]]:
    """
    Messages stored in Redis for this session (human / ai / tool), for UI hydration.
    """
    hist = get_concierge_chat_history(session_id)
    raw = list(hist.messages)
    if len(raw) > limit:
        raw = raw[-limit:]
    out: List[Dict[str, str]] = []
    for m in raw:
        typ = getattr(m, "type", "") or ""
        content = _message_content_to_str(getattr(m, "content", ""))
        if typ == "human":
            out.append({"role": "user", "content": content})
        elif typ == "ai":
            out.append({"role": "assistant", "content": content})
        elif typ == "tool":
            out.append({"role": "tool", "content": content[:4000]})
    return out


def get_concierge_chat_history(session_id: str) -> RedisChatMessageHistory:
    """
    Redis-backed chat history for one concierge session.
    Uses neutral key prefix ``demo:stm`` and a dedicated LC index name.
    """
    return RedisChatMessageHistory(
        session_id=session_id,
        redis_url=config.get_redis_url(),
        key_prefix=config.CONCIERGE_STM_PREFIX,
        index_name=config.CONCIERGE_STM_INDEX,
    )
