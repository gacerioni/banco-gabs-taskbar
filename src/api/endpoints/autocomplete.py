"""
Autocomplete Endpoint
Fast autocomplete suggestions
"""

from fastapi import APIRouter, Query
from typing import List, Dict, Any

from ...data import get_redis_client
from ...search.autocomplete import autocomplete_search


router = APIRouter()


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Query prefix (min 2 chars)"),
    limit: int = Query(10, ge=1, le=50, description="Max suggestions")
) -> Dict[str, Any]:
    """
    Autocomplete endpoint.

    Returns suggestions based on query prefix using Redis FT.SUGGET.
    """
    redis_client = get_redis_client()

    raw_suggestions = autocomplete_search(
        redis_client=redis_client,
        query=q,
        limit=limit
    )

    # Format for frontend: extract doc type and details from payload
    suggestions = []
    for item in raw_suggestions:
        payload = item.get('payload', '')
        # Payload format: "type:id" (e.g., "route:pix_001")
        parts = payload.split(':', 1)
        doc_type = parts[0] if len(parts) > 0 else 'unknown'

        suggestions.append({
            'title': item['suggestion'],
            'subtitle': f"{doc_type.capitalize()}",
            'type': doc_type,
            'icon': get_icon(doc_type),
            'category': doc_type
        })

    return {'suggestions': suggestions}


def get_icon(doc_type: str) -> str:
    """Get icon for document type"""
    icons = {
        'route': '🔗',
        'product': '💼',
        'sku': '🛍️'
    }
    return icons.get(doc_type, '📌')

