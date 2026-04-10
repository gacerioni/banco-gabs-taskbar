"""
Seed Data Loader
Loads all seed data from JSONL files

Easy to maintain:
- Edit JSONL files directly
- No code changes needed
- Hot reload with /seed endpoint
"""

import json
import os
from typing import Dict, List
from pathlib import Path


# ============================================================================
# PATHS
# ============================================================================

SEED_DIR = Path(__file__).parent
ROUTER_EXAMPLES_DIR = SEED_DIR / "router_examples"


# ============================================================================
# ROUTER EXAMPLES LOADER
# ============================================================================

def load_router_examples() -> Dict[str, Dict[str, List[str]]]:
    """
    Load router examples from JSONL files.
    
    Returns:
        Dict with structure:
        {
            'pt': {'search': [...], 'chat': [...]},
            'en': {'search': [...], 'chat': [...]},
            'es': {'search': [...], 'chat': [...]}
        }
    """
    examples = {
        'pt': {'search': [], 'chat': []},
        'en': {'search': [], 'chat': []},
        'es': {'search': [], 'chat': []}
    }
    
    # Load each file
    files = [
        ('pt', 'search', 'pt_search.jsonl'),
        ('pt', 'chat', 'pt_chat.jsonl'),
        ('en', 'search', 'en_search.jsonl'),
        ('en', 'chat', 'en_chat.jsonl'),
        ('es', 'search', 'es_search.jsonl'),
        ('es', 'chat', 'es_chat.jsonl'),
    ]
    
    for lang, intent, filename in files:
        filepath = ROUTER_EXAMPLES_DIR / filename
        
        if not filepath.exists():
            print(f"⚠️  Router examples file not found: {filepath}")
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    example = data.get('example', '').strip()
                    
                    if example:
                        examples[lang][intent].append(example)
            
            count = len(examples[lang][intent])
            print(f"✅ Loaded {count} examples from {filename}")
        
        except Exception as e:
            print(f"❌ Error loading {filepath}: {e}")
    
    # Summary
    print()
    print("📊 Router Examples Summary:")
    for lang in ['pt', 'en', 'es']:
        search_count = len(examples[lang]['search'])
        chat_count = len(examples[lang]['chat'])
        print(f"   {lang.upper()}: {search_count} search, {chat_count} chat")
    
    return examples


# ============================================================================
# BANKING DATA LOADERS
# ============================================================================

def load_routes() -> List[Dict]:
    """Load banking routes from routes.jsonl"""
    filepath = SEED_DIR / "routes.jsonl"
    routes = []
    
    if not filepath.exists():
        print(f"⚠️  Routes file not found: {filepath}")
        return routes
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    routes.append(json.loads(line))
        print(f"✅ Loaded {len(routes)} routes")
    except Exception as e:
        print(f"❌ Error loading routes: {e}")
    
    return routes


def load_products() -> List[Dict]:
    """Load banking products from products.jsonl"""
    filepath = SEED_DIR / "products.jsonl"
    products = []
    
    if not filepath.exists():
        print(f"⚠️  Products file not found: {filepath}")
        return products
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    products.append(json.loads(line))
        print(f"✅ Loaded {len(products)} products")
    except Exception as e:
        print(f"❌ Error loading products: {e}")
    
    return products


def load_skus() -> List[Dict]:
    """Load marketplace SKUs from skus.jsonl"""
    filepath = SEED_DIR / "skus.jsonl"
    skus = []
    
    if not filepath.exists():
        print(f"⚠️  SKUs file not found: {filepath}")
        return skus
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    skus.append(json.loads(line))
        print(f"✅ Loaded {len(skus)} SKUs")
    except Exception as e:
        print(f"❌ Error loading SKUs: {e}")
    
    return skus

