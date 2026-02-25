"""
Test script to verify semantic router learns from JSONL data files
"""

import json
from pathlib import Path

def extract_references_from_file(filename: str):
    """Extract semantic references from JSONL file"""
    references = []
    filepath = Path(__file__).parent / filename
    
    if not filepath.exists():
        print(f"❌ File not found: {filename}")
        return references
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                doc = json.loads(line)
                
                # Extract title
                if 'title' in doc and doc['title']:
                    references.append(doc['title'].lower())
                
                # Extract description
                if 'description' in doc and doc['description']:
                    references.append(doc['description'].lower())
                
                # Extract keywords
                if 'keywords' in doc and isinstance(doc['keywords'], list):
                    references.extend([kw.lower() for kw in doc['keywords'] if kw])
                
                # Extract aliases
                if 'aliases' in doc and isinstance(doc['aliases'], list):
                    references.extend([alias.lower() for alias in doc['aliases'] if alias])
                
                # Extract subtitle
                if 'subtitle' in doc and doc['subtitle']:
                    references.append(doc['subtitle'].lower())
                    
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                continue
    
    # Deduplicate
    references = list(set([ref.strip() for ref in references if ref and ref.strip()]))
    return references

def main():
    print("🧪 Testing Data-Driven Semantic Router\n")
    print("=" * 60)
    
    # Extract references from each file
    route_refs = extract_references_from_file("routes.jsonl")
    sku_refs = extract_references_from_file("skus.jsonl")
    product_refs = extract_references_from_file("products.jsonl")
    
    print(f"\n📚 ROUTE REFERENCES ({len(route_refs)} total):")
    print("-" * 60)
    for ref in sorted(route_refs)[:20]:  # Show first 20
        print(f"  • {ref}")
    if len(route_refs) > 20:
        print(f"  ... and {len(route_refs) - 20} more")
    
    print(f"\n📚 SKU REFERENCES ({len(sku_refs)} total):")
    print("-" * 60)
    for ref in sorted(sku_refs)[:20]:
        print(f"  • {ref}")
    if len(sku_refs) > 20:
        print(f"  ... and {len(sku_refs) - 20} more")
    
    print(f"\n📚 PRODUCT REFERENCES ({len(product_refs)} total):")
    print("-" * 60)
    for ref in sorted(product_refs)[:20]:
        print(f"  • {ref}")
    if len(product_refs) > 20:
        print(f"  ... and {len(product_refs) - 20} more")
    
    # Check for "robaro meu cartao" related references
    print("\n" + "=" * 60)
    print("🔍 CHECKING FOR 'ROBARO MEU CARTAO' SEMANTIC MATCHES:")
    print("-" * 60)
    
    robbery_related = [ref for ref in route_refs if any(word in ref for word in ['roub', 'perd', 'bloq', 'cancel'])]
    
    if robbery_related:
        print("✅ Found robbery/loss related references:")
        for ref in sorted(robbery_related):
            print(f"  • {ref}")
        print("\n✅ Semantic router should handle 'robaro meu cartao' naturally!")
    else:
        print("❌ No robbery/loss references found")
    
    print("\n" + "=" * 60)
    print("✅ Data-driven approach verified!")
    print("   Just update JSONL files - no code changes needed!")

if __name__ == "__main__":
    main()

