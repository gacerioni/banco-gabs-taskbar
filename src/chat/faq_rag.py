"""
Lightweight FAQ RAG for the concierge: embeddings match hybrid search (HFTextVectorizer).

Data lives in Redis under ``demo:concierge:faq`` as JSON (chunks + embedding matrix).
Swap or extend ``src/data/seed/concierge_faq.json`` and re-seed to evolve the demo narrative.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import redis

from ..core.config import config
from ..search.vectorizer import embed_text, embed_texts


def _faq_json_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "seed" / "concierge_faq.json"


def seed_concierge_faq(redis_client: redis.Redis) -> int:
    """
    Load FAQ JSON, embed each chunk (question + answer preview), store in Redis.
    Returns number of chunks indexed.
    """
    path = _faq_json_path()
    if not path.exists():
        print(f"⚠️  Concierge FAQ file not found: {path}")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        rows: List[Dict[str, Any]] = json.load(f)

    if not rows:
        return 0

    texts = []
    for row in rows:
        q = str(row.get("question", "")).strip()
        a = str(row.get("answer", "")).strip()
        texts.append(f"{q}\n{a[:200]}")

    print(f"🔢 Embedding {len(rows)} concierge FAQ chunks...")
    embeddings = embed_texts(texts)
    mat = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms

    payload = {
        "version": 1,
        "chunks": [
            {"id": r.get("id", f"faq_{i}"), "question": r.get("question", ""), "answer": r.get("answer", "")}
            for i, r in enumerate(rows)
        ],
        "embedding_dim": int(mat.shape[1]),
        "embeddings": mat.tolist(),
    }

    redis_client.set(config.CONCIERGE_FAQ_REDIS_KEY, json.dumps(payload, ensure_ascii=False))
    print(f"✅ Stored concierge FAQ RAG ({len(rows)} chunks) at {config.CONCIERGE_FAQ_REDIS_KEY}")
    return len(rows)


def _load_kb(redis_client: redis.Redis) -> Tuple[List[Dict[str, Any]], np.ndarray] | None:
    raw = redis_client.get(config.CONCIERGE_FAQ_REDIS_KEY)
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    chunks = data.get("chunks") or []
    emb = data.get("embeddings") or []
    if not chunks or not emb or len(chunks) != len(emb):
        return None
    mat = np.array(emb, dtype=np.float32)
    return chunks, mat


def retrieve_faq_context(redis_client: redis.Redis, query: str, k: int | None = None) -> str:
    """
    Cosine similarity over precomputed FAQ embeddings (same model as search).
    Returns a compact string for the system prompt, or empty string if KB missing.
    """
    if not query or not str(query).strip():
        return ""

    loaded = _load_kb(redis_client)
    if not loaded:
        return ""

    chunks, mat = loaded
    k = k if k is not None else config.CONCIERGE_FAQ_TOP_K
    k = max(1, min(k, len(chunks)))

    q = np.array(embed_text(query.strip()), dtype=np.float32)
    qn = np.linalg.norm(q)
    if qn == 0:
        return ""
    q = q / qn

    sims = mat @ q
    top_idx = np.argsort(-sims)[:k]

    lines: List[str] = []
    for rank, idx in enumerate(top_idx, start=1):
        c = chunks[int(idx)]
        score = float(sims[int(idx)])
        lines.append(
            f"[{rank}] (score={score:.3f}) Q: {c.get('question','')}\n    A: {c.get('answer','')}"
        )
    return "\n".join(lines)
