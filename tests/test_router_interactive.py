#!/usr/bin/env python3
"""
Interactive Router Tester
Test language detection + semantic routing in real-time
"""

import sys
from semantic_router import route_query, print_routing_info

def print_banner():
    print("=" * 80)
    print("🔀 INTERACTIVE SEMANTIC ROUTER TESTER")
    print("=" * 80)
    print()
    print("Test language detection (PT/EN/ES) + intent routing (search vs chat)")
    print()
    print("Commands:")
    print("  - Type any query to test")
    print("  - 'examples' - Show example queries")
    print("  - 'quit' or 'exit' - Exit")
    print()
    print("=" * 80)
    print()


def show_examples():
    print("\n📚 EXAMPLE QUERIES:\n")
    
    print("🇧🇷 PORTUGUÊS - Search:")
    print("  • pix")
    print("  • boleto")
    print("  • investimentos")
    print("  • comprar iphone")
    print()
    
    print("🇧🇷 PORTUGUÊS - Chat:")
    print("  • como funciona o pix?")
    print("  • preciso de ajuda")
    print("  • me explica o cashback")
    print("  • qual a diferença entre CDB e tesouro?")
    print()
    
    print("🇺🇸 ENGLISH - Search:")
    print("  • investments")
    print("  • buy iphone")
    print("  • bill payment")
    print()
    
    print("🇺🇸 ENGLISH - Chat:")
    print("  • how do I invest?")
    print("  • I need help")
    print("  • what is cashback?")
    print()
    
    print("🇪🇸 ESPAÑOL - Search:")
    print("  • inversiones")
    print("  • comprar iphone")
    print()
    
    print("🇪🇸 ESPAÑOL - Chat:")
    print("  • ¿cómo puedo invertir?")
    print("  • necesito ayuda")
    print()


def format_result(query: str, language: str, intent: str, confidence: float):
    """Format result with nice colors and emojis"""

    # Safety checks
    if not language:
        language = 'unknown'
    if not intent:
        intent = 'unknown'
    if confidence is None:
        confidence = 0.0

    # Language emoji
    lang_emoji = {
        'pt': '🇧🇷',
        'en': '🇺🇸',
        'es': '🇪🇸'
    }

    # Intent emoji
    intent_emoji = {
        'search': '🔍',
        'chat': '💬'
    }

    # Confidence color
    if confidence >= 0.9:
        conf_status = "🟢 HIGH"
    elif confidence >= 0.7:
        conf_status = "🟡 MEDIUM"
    else:
        conf_status = "🔴 LOW"

    print()
    print("─" * 80)
    print(f"📝 Query: \"{query}\"")
    print("─" * 80)
    print(f"{lang_emoji.get(language, '🌍')} Language: {language.upper()}")
    print(f"{intent_emoji.get(intent, '❓')} Intent:   {intent.upper()}")
    print(f"{conf_status}   Confidence: {confidence:.1%}")
    print("─" * 80)

    # Explain what will happen
    if intent == 'search':
        print("✅ Action: Will execute HYBRID SEARCH (text + vector)")
        print("   → Returns: Products, routes, banking services")
    elif intent == 'chat':
        print("✅ Action: Will execute CHAT (conversational AI)")
        print("   → Returns: Conversational response (mock or OpenAI)")
    else:
        print("⚠️  Action: Unknown intent - system will default to search")
    print()


def main():
    print_banner()
    
    # Warm up models (load them once)
    print("⏳ Loading models (this takes ~10s first time)...")
    try:
        # Trigger model loading
        route_query("test", default_lang='pt')
        print("✅ Models loaded!\n")
    except Exception as e:
        print(f"❌ Error loading models: {e}\n")
        return
    
    while True:
        try:
            # Get user input
            query = input("🔍 Enter query (or 'examples' / 'quit'): ").strip()
            
            if not query:
                continue
            
            # Handle commands
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if query.lower() in ['examples', 'ex', 'help', 'h']:
                show_examples()
                continue
            
            # Route the query
            language, intent, confidence = route_query(query, default_lang='pt')
            
            # Display result
            format_result(query, language, intent, confidence)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue


if __name__ == "__main__":
    main()

