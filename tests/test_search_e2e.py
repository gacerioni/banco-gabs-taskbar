#!/usr/bin/env python3
"""
End-to-end test for semantic search
Tests that typos and variations work correctly
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_search(query: str, expected_title: str = None):
    """Test a search query"""
    print(f"\n{'='*70}")
    print(f"🔍 Query: '{query}'")
    print(f"{'='*70}")
    
    response = requests.get(f"{BASE_URL}/search", params={"q": query})
    
    if response.status_code != 200:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    
    print(f"⏱️  Latency: {data['latency_ms']}ms")
    print(f"📊 Results: {len(data['results'])}")
    print(f"🎯 Intent: {data.get('intent', 'N/A')}")
    print(f"📈 Strategy: {data.get('strategy', 'N/A')}")
    
    if data['results']:
        print(f"\n🏆 Top Results:")
        for i, result in enumerate(data['results'][:5], 1):
            match_type = result.get('match_type', 'unknown')
            vector_dist = result.get('vector_distance')
            dist_str = f" (dist: {vector_dist:.4f})" if vector_dist is not None else ""
            print(f"  {i}. [{match_type:6}] {result['title']:<30} (score: {result['score']:.2f}){dist_str}")
        
        if expected_title:
            top_result = data['results'][0]
            if expected_title.lower() in top_result['title'].lower():
                print(f"\n✅ SUCCESS: Found expected result '{expected_title}'")
                return True
            else:
                print(f"\n⚠️  WARNING: Expected '{expected_title}', got '{top_result['title']}'")
                return False
    else:
        print("❌ No results found")
        return False
    
    return True

def main():
    print("="*70)
    print("END-TO-END SEMANTIC SEARCH TEST")
    print("="*70)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not healthy!")
            return
        print("✅ Server is healthy\n")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print("   Start it with: source venv/bin/activate && uvicorn main:app --reload")
        return
    
    # Test cases
    test_cases = [
        ("roubaram meu cartao", "Bloquear Cartão"),
        ("robaram meu cartao", "Bloquear Cartão"),  # Missing 'u'
        ("robaro meu cartao", "Bloquear Cartão"),   # Typo
        ("me roubaram", "Bloquear Cartão"),
        ("perdi meu cartao", "Bloquear Cartão"),
        ("pix", "Pix"),
        ("iphone 15", None),  # Should find SKU
        ("investir", "Investimentos"),
    ]
    
    results = []
    for query, expected in test_cases:
        success = test_search(query, expected)
        results.append((query, success))
        time.sleep(0.5)  # Be nice to the server
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for query, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {query}")
    
    print(f"\n📊 Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()

