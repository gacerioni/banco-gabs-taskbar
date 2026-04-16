"""
Short-term memory for concierge: LangChain RedisChatMessageHistory (Redis + index).
"""

from langchain_redis import RedisChatMessageHistory

from ..core.config import config


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
