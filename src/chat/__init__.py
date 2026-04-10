"""
Chat Module
Handles conversational queries routed to 'chat' intent
"""

from .handler import handle_chat_query, get_openai_client

__all__ = ['handle_chat_query', 'get_openai_client']
