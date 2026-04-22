"""
Canned replies when the semantic guard blocks (no LLM).
"""

from __future__ import annotations


def blocked_reply(route: str, language: str) -> str:
    """User-facing message for a blocked guard route."""
    lang = (language or "pt").lower()[:2]

    if route == "abuse_block":
        if lang == "en":
            return (
                "I’m here to help with this bank and marketplace demo only. "
                "I can’t continue when messages are abusive. "
                "Please ask about products, banking FAQs, or your cart."
            )
        if lang == "es":
            return (
                "Solo puedo ayudarte con esta demo del banco y la tienda. "
                "No puedo continuar si el mensaje es ofensivo. "
                "Pregunta por productos, preguntas frecuentes o tu carrito."
            )
        return (
            "Estou aqui só para ajudar nesta demo do banco e marketplace. "
            "Não consigo continuar quando a mensagem é ofensiva. "
            "Pergunte sobre produtos, dúvidas de serviços ou seu carrinho."
        )

    if route == "policy_block":
        if lang == "en":
            return (
                "I can’t help with that request in this demo. "
                "I can assist with sample banking FAQs, marketplace SKUs, prices, stock, and your cart."
            )
        if lang == "es":
            return (
                "No puedo ayudar con esa solicitud en esta demo. "
                "Puedo ayudarte con preguntas bancarias de ejemplo, SKUs, precios, stock y tu carrito."
            )
        return (
            "Não posso ajudar com esse tipo de pedido nesta demonstração. "
            "Posso ajudar com dúvidas de serviços de exemplo, produtos da loja, preços, estoque e carrinho."
        )

    if route == "off_topic":
        if lang == "en":
            return (
                "This assistant only covers the demo bank and marketplace (products, cart, sample FAQs). "
                "Try asking about Pix, cards, investments, or adding a product to your cart."
            )
        if lang == "es":
            return (
                "Este asistente solo cubre el banco y la tienda de demostración. "
                "Prueba a preguntar por Pix, tarjetas, inversiones o añadir un producto al carrito."
            )
        return (
            "Este assistente cobre só o banco e a loja desta demonstração. "
            "Pergunte sobre Pix, cartões, investimentos ou adicionar um produto ao carrinho."
        )

    if lang == "en":
        return "I can’t process that message here. Ask about this demo’s banking or marketplace features."
    if lang == "es":
        return "No puedo procesar ese mensaje aquí. Pregunta por las funciones de esta demo."
    return "Não consigo processar essa mensagem aqui. Pergunte sobre os recursos desta demonstração."
