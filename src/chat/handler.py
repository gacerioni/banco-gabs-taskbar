"""
Chat Handler for Banco Inter Taskbar
Handles conversational queries routed to 'chat' intent

When a query is routed to chat:
1. Mock response showing chat is opening
2. (Optional) Call OpenAI for actual conversational response
3. Return formatted chat response
"""

from typing import Dict, Any, Optional
import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.config import config

# ============================================================================
# OPENAI CLIENT (lazy loaded)
# ============================================================================

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client (lazy loading)"""
    global _openai_client
    
    if _openai_client is None:
        if not config.OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY not set - chat will use mock responses")
            return None
        
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("✅ OpenAI client initialized")
        except ImportError:
            print("⚠️  openai package not installed - chat will use mock responses")
            return None
        except Exception as e:
            print(f"⚠️  Failed to initialize OpenAI client: {e}")
            return None
    
    return _openai_client


# ============================================================================
# SYSTEM PROMPTS (per language)
# ============================================================================

SYSTEM_PROMPTS = {
    'pt': """Você é um assistente virtual do Banco Inter.
Ajude o usuário com dúvidas sobre serviços bancários, investimentos, pagamentos e produtos.
Seja amigável, claro e objetivo.

Serviços disponíveis:
- Pix: Transferências instantâneas
- Boletos: Pagamento de contas
- Investimentos: CDB, Tesouro Direto, Ações
- Empréstimos: Crédito pessoal
- Cartões: Virtual e físico
- Cashback: Dinheiro de volta em compras
- Seguros: Vida, auto, residencial
- Marketplace: Eletrônicos, celulares, notebooks
""",
    
    'en': """You are a virtual assistant for Banco Inter.
Help users with questions about banking services, investments, payments and products.
Be friendly, clear and objective.

Available services:
- Pix: Instant transfers
- Bill payment
- Investments: CDB, Treasury bonds, Stocks
- Loans: Personal credit
- Cards: Virtual and physical
- Cashback: Money back on purchases
- Insurance: Life, auto, home
- Marketplace: Electronics, phones, laptops
""",
    
    'es': """Eres un asistente virtual de Banco Inter.
Ayuda a los usuarios con preguntas sobre servicios bancarios, inversiones, pagos y productos.
Sé amable, claro y objetivo.

Servicios disponibles:
- Pix: Transferencias instantáneas
- Pago de facturas
- Inversiones: CDB, Bonos del tesoro, Acciones
- Préstamos: Crédito personal
- Tarjetas: Virtual y física
- Cashback: Dinero de vuelta en compras
- Seguros: Vida, auto, hogar
- Marketplace: Electrónicos, teléfonos, laptops
"""
}


# ============================================================================
# CHAT HANDLER
# ============================================================================

def handle_chat_query(
    query: str,
    language: str = 'pt',
    use_openai: bool = True
) -> Dict[str, Any]:
    """
    Handle a chat query.
    
    Args:
        query: User question
        language: Language code ('pt', 'en', 'es')
        use_openai: Whether to use OpenAI or mock response
        
    Returns:
        Dict with chat response
    """
    start_time = time.time()
    
    # Try OpenAI if available and requested
    if use_openai:
        client = get_openai_client()
        if client:
            try:
                response_text = get_openai_response(query, language, client)
                latency_ms = (time.time() - start_time) * 1000
                
                return {
                    "type": "chat",
                    "query": query,
                    "language": language,
                    "response": response_text,
                    "provider": "openai",
                    "model": config.OPENAI_MODEL,
                    "latency_ms": round(latency_ms, 2)
                }
            except Exception as e:
                print(f"⚠️  OpenAI call failed: {e}, falling back to mock")
    
    # Fallback to mock response
    response_text = get_mock_response(query, language)
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "type": "chat",
        "query": query,
        "language": language,
        "response": response_text,
        "provider": "mock",
        "model": "none",
        "latency_ms": round(latency_ms, 2)
    }


def get_openai_response(query: str, language: str, client) -> str:
    """Get response from OpenAI"""
    system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS['en'])
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content


def get_mock_response(query: str, language: str) -> str:
    """Get mock response (when OpenAI is not available)"""
    
    responses = {
        'pt': f"""💬 **Chat Agentico Iniciado**

Você perguntou: "{query}"

🤖 Esta é uma resposta mockada. Para usar o chat real com IA, configure a chave da OpenAI:

```bash
export OPENAI_API_KEY=sua-chave-aqui
```

Em produção, esta query seria processada por um agente conversacional que:
- Entende contexto e intenção
- Acessa sistemas do Banco Inter
- Fornece respostas personalizadas
- Pode executar ações (transferências, pagamentos, etc)
""",
        
        'en': f"""💬 **Agentic Chat Started**

You asked: "{query}"

🤖 This is a mock response. To use real AI chat, configure OpenAI key:

```bash
export OPENAI_API_KEY=your-key-here
```

In production, this query would be processed by a conversational agent that:
- Understands context and intent
- Accesses Banco Inter systems
- Provides personalized responses
- Can execute actions (transfers, payments, etc)
""",
        
        'es': f"""💬 **Chat Agéntico Iniciado**

Preguntaste: "{query}"

🤖 Esta es una respuesta simulada. Para usar chat IA real, configure la clave OpenAI:

```bash
export OPENAI_API_KEY=su-clave-aqui
```

En producción, esta consulta sería procesada por un agente conversacional que:
- Entiende contexto e intención
- Accede a sistemas de Banco Inter
- Proporciona respuestas personalizadas
- Puede ejecutar acciones (transferencias, pagos, etc)
"""
    }
    
    return responses.get(language, responses['en'])

