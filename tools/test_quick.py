#!/usr/bin/env python3
"""Quick test of route examples"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routers.route_examples import get_route_examples

examples = get_route_examples()

print("=" * 80)
print("📚 ROUTE EXAMPLES LOADED")
print("=" * 80)
print()

for lang in ['pt', 'en', 'es']:
    print(f"🌍 {lang.upper()}")
    print(f"   Search examples: {len(examples[lang]['search'])}")
    print(f"   Chat examples: {len(examples[lang]['chat'])}")
    print()
    
    if lang == 'pt':
        print("   PT Chat examples (first 10):")
        for ex in examples['pt']['chat'][:10]:
            print(f"     - {ex}")
        print()
        
        # Check if our problem query is there
        if "quero falar com o gerente" in examples['pt']['chat']:
            print("   ✅ 'quero falar com o gerente' IS in PT chat examples!")
        else:
            print("   ❌ 'quero falar com o gerente' NOT FOUND in PT chat examples!")
        print()

print("=" * 80)

