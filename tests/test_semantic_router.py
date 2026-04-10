#!/usr/bin/env python3
"""
Test Semantic Router - Stack C Implementation
Tests language detection + intent routing
"""

import sys
from semantic_router import route_query, print_routing_info

# ============================================================================
# TEST CASES
# ============================================================================

test_cases = [
    # Portuguese - Search intent
    ("pix", "pt", "search"),
    ("boleto", "pt", "search"),
    ("investimentos", "pt", "search"),
    ("comprar iphone", "pt", "search"),
    ("quero um notebook", "pt", "search"),
    
    # Portuguese - Chat intent
    ("como faço pra investir?", "pt", "chat"),
    ("como funciona o pix?", "pt", "chat"),
    ("preciso de ajuda", "pt", "chat"),
    ("me explica o cashback", "pt", "chat"),
    ("qual a diferença entre CDB e tesouro?", "pt", "chat"),
    
    # English - Search intent
    ("pix", "en", "search"),
    ("investments", "en", "search"),
    ("buy iphone", "en", "search"),
    
    # English - Chat intent
    ("how do I invest?", "en", "chat"),
    ("I need help", "en", "chat"),
    ("what is cashback?", "en", "chat"),
    
    # Spanish - Search intent
    ("pix", "es", "search"),
    ("inversiones", "es", "search"),
    
    # Spanish - Chat intent
    ("¿cómo puedo invertir?", "es", "chat"),
    ("necesito ayuda", "es", "chat"),
]


def test_semantic_router():
    """Test the semantic router with various queries"""
    
    print("=" * 80)
    print("🧪 TESTING SEMANTIC ROUTER - Stack C")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for query, expected_lang, expected_intent in test_cases:
        try:
            # Route the query
            language, intent, confidence = route_query(query)
            
            # Check results
            lang_match = language == expected_lang
            intent_match = intent == expected_intent
            
            status = "✅ PASS" if (lang_match and intent_match) else "❌ FAIL"
            
            if lang_match and intent_match:
                passed += 1
            else:
                failed += 1
            
            # Print result
            print(f"{status} | Query: '{query}'")
            print(f"       | Expected: lang={expected_lang}, intent={expected_intent}")
            print(f"       | Got:      lang={language}, intent={intent}, confidence={confidence:.2%}")
            
            if not lang_match:
                print(f"       | ⚠️  Language mismatch!")
            if not intent_match:
                print(f"       | ⚠️  Intent mismatch!")
            
            print()
            
        except Exception as e:
            print(f"❌ ERROR | Query: '{query}'")
            print(f"         | Error: {e}")
            print()
            failed += 1
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {passed/len(test_cases)*100:.1f}%")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_semantic_router()
    sys.exit(0 if success else 1)

