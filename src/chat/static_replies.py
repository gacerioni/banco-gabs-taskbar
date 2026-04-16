"""
Respostas estáticas para mensagens curtas e repetitivas — sem LLM (economia de tokens).
Não cobre pedidos de produto/carrinho; esses seguem para o concierge normal.
"""

from __future__ import annotations

import re
from typing import Optional

_SHOPPING_OR_TASK = (
    "carrinho",
    "comprar",
    "compra",
    "adicion",
    "sku",
    "preço",
    "preco",
    "estoque",
    "notebook",
    "iphone",
    "produto",
    "loja",
    "boleto",
    "fatura",
    "invest",
    "empréstimo",
    "emprestimo",
    "quantos",
    "quanto",
    "tem na",
    "na loja",
    "gerente",
    "atendente",
    "falar com",
    "pix",
    "transfer",
    "cart",
    "buy",
    "add ",
    "remove",
    "r$",
)


def _looks_like_shopping_or_support(q: str) -> bool:
    low = (q or "").lower()
    return any(k in low for k in _SHOPPING_OR_TASK)


def _strip_trailing_punct(s: str) -> str:
    return re.sub(r"[!.?…]+$", "", (s or "").strip()).strip()


def try_static_chat_reply(query: str, language: str) -> Optional[str]:
    """
    Retorna texto fixo se a mensagem for só saudação/agradecimento/despedida curta.
    Caso contrário None (deixa o fluxo normal: mock ou OpenAI).
    """
    raw = (query or "").strip()
    if not raw or len(raw) > 140:
        return None
    if _looks_like_shopping_or_support(raw):
        return None

    lang = (language or "pt").lower()[:2]
    low = _strip_trailing_punct(raw.lower())
    low = re.sub(r"\s+", " ", low)

    if lang == "en":
        if low in ("hi", "hello", "hey", "good morning", "good afternoon", "good evening"):
            return (
                "Hello! I'm the Redis demo concierge — I can help with FAQs, "
                "product search, and your cart. What would you like to do?"
            )
        if low in ("thanks", "thank you", "thx", "ty"):
            return "You're welcome! If you need anything else, just ask."
        if low in ("bye", "goodbye", "see you", "cya"):
            return "Goodbye! Come back anytime."
        if low in ("ok", "okay", "k"):
            return "Got it. Let me know if you need help with products or your cart."
        return None

    # pt (default) + es short paths
    if lang == "es":
        if low in ("hola", "buenos días", "buenas tardes", "buenas noches", "hey"):
            return (
                "¡Hola! Soy el concierge de la demo Redis: FAQ, búsqueda de productos y carrito. "
                "¿En qué te ayudo?"
            )
        if low in ("gracias", "muchas gracias"):
            return "¡De nada! Si necesitas algo más, aquí estoy."
        if low in ("adiós", "hasta luego", "chao"):
            return "¡Hasta pronto!"
        return None

    # Portuguese
    if low in (
        "oi",
        "olá",
        "ola",
        "hey",
        "e aí",
        "eai",
        "opa",
        "bom dia",
        "boa tarde",
        "boa noite",
    ):
        return (
            "Olá! Sou o concierge desta demo Redis: posso ajudar com dúvidas (FAQ), "
            "buscar produtos no inventário e gerenciar seu carrinho. O que você precisa?"
        )

    if low in (
        "obrigado",
        "obrigada",
        "valeu",
        "vlw",
        "agradeço",
        "agradeco",
        "muito obrigado",
        "muito obrigada",
        "thanks",
        "thank you",
    ):
        return "Por nada! Se precisar de mais alguma coisa, é só chamar."

    if low in ("tchau", "até logo", "ate logo", "até mais", "ate mais", "flw", "bye"):
        return "Até logo! Volte quando quiser."

    if low in ("ok", "okay", "beleza", "blz", "certo", "sim", "isso"):
        return "Combinado. Posso buscar um produto, ver o carrinho ou tirar uma dúvida — o que prefere?"

    # Frases muito curtas com saudação + cortesia (sem pedido de produto)
    if re.fullmatch(r"(oi|olá|ola)\s*,?\s*(tudo\s+bem|td\s+bem)\??", low):
        return (
            "Tudo certo por aqui — obrigado por perguntar! "
            "Em que posso ajudar: produtos, carrinho ou alguma dúvida?"
        )

    return None
