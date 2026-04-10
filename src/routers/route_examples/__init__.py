"""
Route Examples - NOW LOADS FROM JSONL FILES!

🎯 TO EDIT EXAMPLES:
→ src/data/seed/router_examples/pt_search.jsonl
→ src/data/seed/router_examples/pt_chat.jsonl
→ src/data/seed/router_examples/en_search.jsonl
→ src/data/seed/router_examples/en_chat.jsonl
→ etc.

Just edit the JSONL file and restart or reload router!
No code changes needed! 🎉
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.data.seed import load_router_examples


def get_route_examples():
    """
    Get all route examples organized by language and intent.
    
    NOW LOADS FROM JSONL FILES!
    Edit: src/data/seed/router_examples/*.jsonl
    
    Returns:
        Dict with structure:
        {
            'pt': {'search': [...], 'chat': [...]},
            'en': {'search': [...], 'chat': [...]},
            'es': {'search': [...], 'chat': [...]}
        }
    """
    return load_router_examples()


__all__ = ['get_route_examples']

