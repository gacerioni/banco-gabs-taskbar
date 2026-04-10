"""
Redis Index Schemas
All FT.CREATE schemas with Redis 8.6 HYBRID search support
"""

from . import route_schema
from . import product_schema
from . import sku_schema

__all__ = [
    'route_schema',
    'product_schema',
    'sku_schema',
]
