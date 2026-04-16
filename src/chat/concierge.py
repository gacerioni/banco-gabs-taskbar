"""
Concierge: OpenAI tool-calling over Redis hybrid SKU search + cart (Hash).
"""

import json
import time
from typing import Any, Dict, List, Optional

import redis
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from ..core.config import config
from ..data.models import sku_schema
from ..search.hybrid_search import hybrid_search, build_fts_prefix_query
from .faq_rag import retrieve_faq_context
from .stm_memory import get_concierge_chat_history
from ..cart.store import (
    get_cart_snapshot,
    add_line,
    set_line_quantity,
    remove_line,
    clear_cart,
    fetch_sku_doc,
)


def _system_prompt(language: str) -> str:
    base = (
        "You are the marketplace concierge for this Redis demo app (sample banking routes + SKU inventory). "
        "Use tools for every fact about products, prices, stock, and the shopping cart. "
        "Never invent sku_id values — only use sku_id strings returned by search_inventory. "
        "Immediately before add_to_cart, call search_inventory for the exact product the user requested "
        "(or the item you just described) and pick the matching sku_id from those results — "
        "do not reuse a sku_id from an unrelated earlier topic. "
        "If in_stock is false, warn the user before adding; if they confirm, you may still add and note it. "
        "Reply in the user's language ({lang}). Be concise and helpful."
    )
    lang = (language or "pt").lower()
    if lang == "pt":
        return (
            "Você é o concierge do marketplace desta demo Redis (rotas bancárias fictícias + inventário de SKUs de exemplo). "
            "Use sempre as ferramentas para preços, estoque e carrinho — não invente dados. "
            "Use apenas sku_id retornados por search_inventory. "
            "Antes de cada add_to_cart, chame search_inventory de novo com o nome do produto que o usuário pediu "
            "(ou o mesmo item que você acabou de descrever na conversa) e use o sku_id da linha que corresponde "
            "a esse produto — nunca reutilize um sku_id de outro assunto ou de um produto que o usuário não pediu. "
            "Se houver vários SKUs parecidos, confirme com o usuário ou escolha o que bate com o título que você citou. "
            "Se em_estoque=false, avise; só adicione se o usuário insistir. "
            "Responda em português do Brasil, de forma clara e breve."
        )
    if lang == "es":
        return base.format(lang="español")
    return base.format(lang="English")


def _system_with_faq(redis_client: redis.Redis, query: str, language: str) -> str:
    """Base system prompt + optional FAQ RAG block (same embeddings as hybrid search)."""
    base = _system_prompt(language or "pt")
    try:
        faq = retrieve_faq_context(
            redis_client,
            query,
            k=config.CONCIERGE_FAQ_TOP_K,
        )
    except Exception as e:
        print(f"⚠️  FAQ RAG retrieve failed: {e}")
        faq = ""
    if faq.strip():
        lang = (language or "pt").lower()[:2]
        if lang == "en":
            header = "\n\n--- FAQ (Redis RAG — retrieved snippets; use when relevant) ---\n"
        elif lang == "es":
            header = "\n\n--- FAQ (Redis RAG — fragmentos recuperados; úsalos si aplica) ---\n"
        else:
            header = (
                "\n\n--- FAQ (Redis RAG — trechos recuperados por similaridade; use se fizer sentido) ---\n"
            )
        base += header + faq
    return base


def _sku_inventory_ft_search_only(
    redis_client: redis.Redis, q: str, limit: int
) -> List[Dict[str, Any]]:
    """
    FT.SEARCH text-only on ``idx:skus`` — used **only** by the concierge ``search_inventory``
    tool when FT.HYBRID returns no SKU rows (e.g. odd phrasing). Global taskbar search stays HYBRID-only.
    """
    fts = build_fts_prefix_query((q or "").strip() or "*")
    idx = sku_schema.INDEX_NAME
    try:
        raw = redis_client.execute_command(
            "FT.SEARCH", idx, fts, "LIMIT", "0", str(max(1, limit))
        )
    except Exception as e:
        print(f"Concierge SKU FT.SEARCH on {idx}: {e}")
        return []
    if not isinstance(raw, (list, tuple)) or len(raw) < 1:
        return []
    try:
        n = int(raw[0])
    except (TypeError, ValueError):
        return []
    if n <= 0:
        return []
    keys: List[str] = []
    i = 1
    while i < len(raw):
        doc_key = raw[i]
        if isinstance(doc_key, bytes):
            doc_key = doc_key.decode()
        keys.append(doc_key)
        i += 2
    if not keys:
        return []
    pipe = redis_client.pipeline(transaction=False)
    for doc_key in keys:
        pipe.json().get(doc_key)
    rows = pipe.execute(raise_on_error=False)
    out: List[Dict[str, Any]] = []
    for doc in rows:
        if doc and isinstance(doc, dict) and doc.get("type") == "sku":
            doc = dict(doc)
            doc.pop("embedding", None)
            doc["_hybrid_score"] = 0.01
            doc["match_type"] = "concierge_ft_text"
            out.append(doc)
    return out


def _format_search_hits(docs: List[Dict[str, Any]], max_items: int = 10) -> str:
    lines = []
    for d in docs[:max_items]:
        sid = d.get("id", "")
        title = d.get("title", "")
        price = d.get("price", "")
        brand = d.get("brand", "")
        stock = d.get("in_stock", True)
        lines.append(
            f"- sku_id={sid} | {title} | brand={brand} | price_BRL={price} | in_stock={stock}"
        )
    if not lines:
        return "(no SKUs found)"
    return "\n".join(lines)


def build_tools(redis_client: redis.Redis, session_id: str, lang: str) -> List[StructuredTool]:
    sid = session_id

    def search_inventory(query: str) -> str:
        """Search marketplace SKUs by product name, brand, or description. Call before adding to cart."""
        docs, _meta = hybrid_search(
            redis_client,
            query.strip(),
            lang=lang,
            country="BR",
            limit=12,
            indexes=["idx:skus"],
        )
        skus_only = [d for d in docs if d.get("type") == "sku"]
        if not skus_only:
            skus_only = _sku_inventory_ft_search_only(
                redis_client, query.strip(), limit=12
            )
        return _format_search_hits(skus_only, 12)

    def get_cart() -> str:
        """Return current cart lines and subtotal."""
        snap = get_cart_snapshot(redis_client, sid)
        if not snap["items"]:
            return "Cart is empty."
        parts = [f"Subtotal BRL {snap['subtotal']:.2f} ({snap['line_count']} lines):"]
        for it in snap["items"]:
            parts.append(
                f"  - {it['sku_id']}: {it['title']} x{it['qty']} @ {it['unit_price']:.2f} = {it['line_total']:.2f}"
            )
        return "\n".join(parts)

    def add_to_cart(sku_id: str, quantity: int = 1) -> str:
        """Add SKU to cart. Call search_inventory immediately before this with the product the user asked for; sku_id must appear in those results (e.g. sku_033). quantity defaults to 1."""
        doc = fetch_sku_doc(redis_client, sku_id)
        if not doc:
            return f"SKU not found: {sku_id}. Call search_inventory first."
        qty = int(quantity) if quantity is not None else 1
        if qty < 1:
            qty = 1
        line_id = str(doc.get("id", sku_id))
        title = str(doc.get("title", sku_id))
        price = float(doc.get("price") or 0)
        stock = bool(doc.get("in_stock", True))
        snap = add_line(redis_client, sid, line_id, qty, title, price, stock)
        return (
            f"OK. Cart: {snap['line_count']} lines, subtotal BRL {snap['subtotal']:.2f}. "
            f"Items: {json.dumps(snap['items'], ensure_ascii=False)}"
        )

    def set_quantity(sku_id: str, quantity: int) -> str:
        """Set absolute quantity for a line; use 0 to remove."""
        snap = set_line_quantity(redis_client, sid, sku_id, int(quantity))
        return f"Cart: {snap['line_count']} lines, subtotal BRL {snap['subtotal']:.2f}"

    def remove_from_cart(sku_id: str) -> str:
        """Remove one SKU line completely."""
        snap = remove_line(redis_client, sid, sku_id)
        return f"Removed. Cart: {snap['line_count']} lines, subtotal BRL {snap['subtotal']:.2f}"

    def empty_cart() -> str:
        """Clear all items from the cart."""
        snap = clear_cart(redis_client, sid)
        return f"Cart cleared. Lines: {snap['line_count']}."

    return [
        StructuredTool.from_function(search_inventory),
        StructuredTool.from_function(get_cart),
        StructuredTool.from_function(add_to_cart),
        StructuredTool.from_function(set_quantity),
        StructuredTool.from_function(remove_from_cart),
        StructuredTool.from_function(empty_cart),
    ]


def run_concierge(
    redis_client: redis.Redis,
    query: str,
    session_id: str,
    language: str = "pt",
    include_tool_trace: bool = False,
) -> Dict[str, Any]:
    """
    Run tool-calling concierge loop. Caller must ensure OPENAI_API_KEY is set.
    """
    tools = build_tools(redis_client, session_id, language or "pt")
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
        temperature=0.15,
        timeout=90,
    )
    llm_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}
    start = time.time()

    stm_hist = None
    try:
        stm_hist = get_concierge_chat_history(session_id)
        prior = list(stm_hist.messages)[-config.CONCIERGE_STM_MAX_MESSAGES :]
    except Exception as e:
        print(f"⚠️  STM load failed (continuing without history): {e}")
        prior = []

    messages: List[Any] = [
        SystemMessage(content=_system_with_faq(redis_client, query, language or "pt")),
        *prior,
        HumanMessage(content=query),
    ]
    trace: List[Dict[str, Any]] = []
    max_steps = 10
    final_text = ""
    tool_calls_total = 0
    llm_rounds = 0

    for step_idx in range(max_steps):
        llm_rounds = step_idx + 1
        ai_msg = llm_tools.invoke(messages)
        messages.append(ai_msg)
        if not isinstance(ai_msg, AIMessage):
            final_text = str(getattr(ai_msg, "content", "") or "").strip()
            break

        tcalls = getattr(ai_msg, "tool_calls", None) or []
        if not tcalls:
            final_text = (ai_msg.content or "").strip()
            break

        for tc in tcalls:
            tool_calls_total += 1
            name = tc.get("name", "")
            args = tc.get("args") or {}
            tid = tc.get("id") or ""
            fn = tool_map.get(name)
            try:
                out = fn.invoke(args) if fn else f"unknown tool: {name}"
            except Exception as e:
                out = f"tool error: {e}"
            if include_tool_trace:
                trace.append(
                    {
                        "name": name,
                        "args": args,
                        "result_preview": str(out)[:500],
                    }
                )
            messages.append(ToolMessage(content=str(out), tool_call_id=tid))
    else:
        final_text = (
            messages[-1].content
            if messages and hasattr(messages[-1], "content") and messages[-1].content
            else "Agent step limit reached."
        )

    if not (final_text or "").strip():
        for m in reversed(messages):
            if isinstance(m, AIMessage) and (getattr(m, "content", None) or "").strip():
                final_text = str(m.content).strip()
                break
    if not (final_text or "").strip():
        final_text = "Não foi possível concluir a resposta — verifique o carrinho abaixo ou tente novamente."

    if stm_hist is not None:
        try:
            stm_hist.add_user_message(query)
            stm_hist.add_ai_message(final_text)
        except Exception as e:
            print(f"⚠️  STM persist failed: {e}")

    snap = get_cart_snapshot(redis_client, session_id)
    elapsed_ms = round((time.time() - start) * 1000, 2)
    sid_short = (session_id or "")[:12]
    print(
        f"📊 concierge_telemetry session={sid_short}… "
        f"tool_calls={tool_calls_total} llm_rounds={llm_rounds} latency_ms={elapsed_ms}"
    )

    return {
        "response": final_text or "(no assistant text)",
        "provider": "openai_concierge",
        "model": config.OPENAI_MODEL,
        "latency_ms": elapsed_ms,
        "cart": snap,
        "tool_trace": trace if include_tool_trace else None,
    }


def _mock_is_shopping_query(q: str) -> bool:
    low = (q or "").lower()
    keys = (
        "carrinho",
        "comprar",
        "adicion",
        "iphone",
        "sku",
        "produto",
        "market",
        "notebook",
        "smartphone",
        "preço",
        "preco",
        "estoque",
        "loja",
        "pix",  # buying context sometimes
    )
    return any(k in low for k in keys)


def _mock_is_handoff_query(q: str) -> bool:
    low = (q or "").lower()
    keys = (
        "gerente",
        "gerência",
        "gerencia",
        "humano",
        "atendente",
        "pessoa",
        "falar com alguém",
        "falar com alguem",
        "ligar",
        "telefone",
        "sac",
        "ouvidoria",
        "reclama",
        "suporte humano",
    )
    return any(k in low for k in keys)


def _format_mixed_hits(docs: List[Dict[str, Any]], max_items: int = 6) -> str:
    lines = []
    for d in docs[:max_items]:
        typ = d.get("type", "?")
        title = d.get("title", "")
        sub = d.get("subtitle", "")
        extra = f" — {sub}" if sub else ""
        lines.append(f"- [{typ}] {title}{extra}")
    return "\n".join(lines) if lines else "(nenhum item encontrado na busca de exemplo)"


def run_concierge_mock(
    redis_client: redis.Redis,
    query: str,
    session_id: str,
    language: str = "pt",
) -> Dict[str, Any]:
    """
    Sem OpenAI: conversa curta em PT/EN com FAQ (RAG) + sugestões Redis.
    Não é 'abrir outro app' — o painel roxo *é* o modo conversa desta mesma página.
    """
    t0 = time.time()
    lang = (language or "pt").lower()
    q = (query or "").strip() or "ajuda"
    snap = get_cart_snapshot(redis_client, session_id)

    faq_block = ""
    try:
        faq_block = retrieve_faq_context(redis_client, q, k=3)
    except Exception:
        faq_block = ""

    shopping = _mock_is_shopping_query(q)
    handoff = _mock_is_handoff_query(q)

    lines: List[str] = []

    if lang.startswith("pt"):
        lines.append("**Concierge (modo demonstração, sem GPT no servidor)**")
        lines.append("")
        if handoff:
            lines.append(
                "Entendi — você quer **falar com alguém** (gerente/atendente). "
                "Isto aqui é **só uma demo técnica**: não existe fila humana, telefone nem conta real."
            )
            lines.append(
                "Em um app de verdade, esse pedido abriria o **canal oficial** (chat do banco, SAC, agência)."
            )
        elif shopping:
            lines.append(
                "Pelo inventário de exemplo dá para **ver SKUs** abaixo; para **montar o carrinho em linguagem natural** "
                "precisa de `OPENAI_API_KEY` no `.env` (o servidor chama o GPT com ferramentas Redis)."
            )
        else:
            lines.append(
                "Você está no **modo conversa** desta mesma barra: não é outra tela. "
                "Sem chave OpenAI eu respondo com **texto fixo + FAQ** recuperado do Redis; com chave, o modelo conversa e usa carrinho/inventário."
            )
        lines.append("")
        if faq_block.strip():
            lines.append("**Trechos da FAQ (RAG no Redis):**")
            lines.append(faq_block)
            lines.append("")
        if shopping:
            docs, _ = hybrid_search(
                redis_client,
                q,
                lang=lang[:2] or "pt",
                country="BR",
                limit=10,
                indexes=["idx:skus"],
            )
            skus = [d for d in docs if d.get("type") == "sku"][:6]
            lines.append("**SKUs parecidos com o que você escreveu:**")
            lines.append(_format_search_hits(skus, 6) if skus else "(nenhum SKU — tente 'iPhone' ou 'cafeteira')")
        else:
            docs, _ = hybrid_search(
                redis_client,
                q,
                lang=lang[:2] or "pt",
                country="BR",
                limit=10,
                indexes=None,
            )
            lines.append("**Sugestões da busca global (rotas/produtos/SKUs de exemplo):**")
            lines.append(_format_mixed_hits(docs, 6))
        lines.append("")
        if snap["items"]:
            lines.append(f"**Seu carrinho (Redis, subtotal BRL {snap['subtotal']:.2f}):**")
            for it in snap["items"]:
                lines.append(f"- {it['title']} ×{it['qty']}")
        else:
            lines.append("**Carrinho:** vazio (sessão guardada no Redis).")
    else:
        lines.append("**Concierge (demo, no OpenAI key on server)**")
        lines.append("")
        if handoff:
            lines.append("There is **no human queue** in this technical demo.")
        elif shopping:
            lines.append("SKU hints below; **natural-language cart** needs `OPENAI_API_KEY`.")
        else:
            lines.append("This purple panel **is** chat mode for this taskbar.")
        lines.append("")
        if faq_block.strip():
            lines.append("**FAQ (Redis RAG):**")
            lines.append(faq_block)
            lines.append("")
        idxs = ["idx:skus"] if shopping else None
        docs, _ = hybrid_search(redis_client, q, lang="en", country="BR", limit=10, indexes=idxs)
        if shopping:
            skus = [d for d in docs if d.get("type") == "sku"][:6]
            lines.append("**SKUs:**")
            lines.append(_format_search_hits(skus, 6) if skus else "(none)")
        else:
            lines.append("**Search hints:**")
            lines.append(_format_mixed_hits(docs, 6))
        lines.append("")
        lines.append(f"**Cart:** {snap['line_count']} line(s).")

    return {
        "response": "\n".join(lines),
        "provider": "mock",
        "model": "none",
        "latency_ms": round((time.time() - t0) * 1000, 2),
        "cart": snap,
        "tool_trace": None,
    }
