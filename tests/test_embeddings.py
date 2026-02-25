#!/usr/bin/env python3
"""
Test script to verify semantic embeddings work correctly
"""

import sys
sys.path.insert(0, '.')

from main import embed_text_real
import numpy as np

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_semantic_similarity():
    """Test that semantically similar phrases have high similarity"""
    
    print("=" * 70)
    print("TESTING SEMANTIC EMBEDDINGS")
    print("=" * 70)
    
    # Test cases: variations of "robaram meu cartao"
    test_phrases = [
        "roubaram meu cartao",      # Correct spelling
        "robaram meu cartao",        # Missing 'u'
        "robaro meu cartao",         # Typo
        "me roubaram",               # Short form
        "bloquear cartao",           # Related action
        "perdi meu cartao",          # Related scenario
        "pix",                       # Unrelated
        "iphone 15"                  # Very unrelated
    ]
    
    print("\n📊 Generating embeddings...")
    embeddings = {}
    for phrase in test_phrases:
        embeddings[phrase] = embed_text_real(phrase)
        print(f"  ✓ {phrase}")
    
    print("\n📈 Similarity Matrix:")
    print("-" * 70)
    
    base_phrase = "roubaram meu cartao"
    base_embedding = embeddings[base_phrase]
    
    print(f"\nBase phrase: '{base_phrase}'")
    print(f"{'Phrase':<30} {'Similarity':>10} {'Status':>15}")
    print("-" * 70)
    
    for phrase in test_phrases:
        if phrase == base_phrase:
            continue
        
        similarity = cosine_similarity(base_embedding, embeddings[phrase])
        
        # Determine status
        if similarity > 0.8:
            status = "✅ VERY HIGH"
        elif similarity > 0.6:
            status = "✅ HIGH"
        elif similarity > 0.4:
            status = "⚠️  MEDIUM"
        else:
            status = "❌ LOW"
        
        print(f"{phrase:<30} {similarity:>10.4f} {status:>15}")
    
    print("\n" + "=" * 70)
    print("EXPECTED RESULTS:")
    print("  - 'robaram meu cartao' should have HIGH similarity (>0.8)")
    print("  - 'robaro meu cartao' should have HIGH similarity (>0.7)")
    print("  - 'me roubaram' should have MEDIUM-HIGH similarity (>0.6)")
    print("  - 'bloquear cartao' should have MEDIUM similarity (>0.5)")
    print("  - 'pix' should have LOW similarity (<0.3)")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_semantic_similarity()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

