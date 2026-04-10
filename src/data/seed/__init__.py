"""
Seed Data Module
All seed data loaders in one place
"""

from .loader import (
    load_router_examples,
    load_routes,
    load_products,
    load_skus
)

__all__ = [
    'load_router_examples',
    'load_routes',
    'load_products',
    'load_skus'
]
