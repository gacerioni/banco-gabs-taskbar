"""
Semantic guard for concierge (RedisVL SemanticRouter).

Classifies user text into commerce / banking_faq / social / off_topic / policy_block / abuse_block.
Blocking routes short-circuit before the LLM. Search bar is unchanged.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from redisvl.extensions.router import Route, SemanticRouter, RoutingConfig
from redisvl.extensions.router.semantic import DistanceAggregationMethod

from ..core.config import config
from ..search.vectorizer import get_search_vectorizer


BLOCKING_ROUTES = frozenset({"abuse_block", "policy_block", "off_topic"})

_guard_router: Optional[SemanticRouter] = None


def _examples_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "seed" / "guard_examples.json"


def load_guard_examples() -> Dict[str, List[str]]:
    path = _examples_path()
    if not path.is_file():
        raise FileNotFoundError(f"Guard examples not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    for name, refs in data.items():
        if isinstance(refs, list) and all(isinstance(r, str) and r.strip() for r in refs):
            out[name] = [r.strip() for r in refs]
        else:
            raise ValueError(f"Invalid guard examples for route '{name}'")
    required = {"commerce", "banking_faq", "social", "off_topic", "policy_block", "abuse_block"}
    missing = required - set(out.keys())
    if missing:
        raise ValueError(f"guard_examples.json missing routes: {missing}")
    return out


def _dist_to_conf(distance: Optional[float]) -> float:
    if distance is None:
        return 0.5
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, 1.0 - d))


@dataclass
class GuardClassification:
    route: str
    confidence: float
    distance: float
    second_route: Optional[str]
    second_confidence: float
    margin: float
    latency_ms: float
    blocked: bool


def get_guard_router(overwrite: bool = False) -> SemanticRouter:
    global _guard_router
    if _guard_router is not None and not overwrite:
        return _guard_router

    examples = load_guard_examples()
    routes = [
        Route(
            name=name,
            references=refs,
            metadata={"kind": "guard", "route": name},
            distance_threshold=0.62,
        )
        for name, refs in examples.items()
    ]

    router = SemanticRouter(
        name="concierge_guard_v1",
        routes=routes,
        routing_config=RoutingConfig(
            aggregation_method=DistanceAggregationMethod.min,
            max_k=6,
        ),
        vectorizer=get_search_vectorizer(),
        redis_url=config.REDIS_URL,
        overwrite=overwrite,
    )
    _guard_router = router
    print("Semantic guard router initialized (concierge_guard_v1)")
    return router


def force_reload_guard_router() -> None:
    global _guard_router
    _guard_router = None
    get_guard_router(overwrite=True)
    print("Semantic guard router reloaded (overwrite=True)")


def classify_concierge_guard(query: str) -> GuardClassification:
    """
    Run RedisVL semantic classification for concierge guardrails.
    """
    t0 = time.time()
    if not config.GUARD_ENABLED:
        return GuardClassification(
            route="commerce",
            confidence=1.0,
            distance=0.0,
            second_route=None,
            second_confidence=0.0,
            margin=1.0,
            latency_ms=0.0,
            blocked=False,
        )

    q = (query or "").strip()
    if not q:
        return GuardClassification(
            route="commerce",
            confidence=1.0,
            distance=0.0,
            second_route=None,
            second_confidence=0.0,
            margin=1.0,
            latency_ms=round((time.time() - t0) * 1000, 2),
            blocked=False,
        )

    router = get_guard_router()
    try:
        matches = router.route_many(statement=q, max_k=4)
    except Exception as e:
        print(f"⚠️  Guard router error: {e} — allowing request")
        return GuardClassification(
            route="commerce",
            confidence=0.5,
            distance=0.5,
            second_route=None,
            second_confidence=0.0,
            margin=0.0,
            latency_ms=round((time.time() - t0) * 1000, 2),
            blocked=False,
        )

    elapsed = round((time.time() - t0) * 1000, 2)

    if not matches or not matches[0].name:
        return GuardClassification(
            route="commerce",
            confidence=0.5,
            distance=0.5,
            second_route=None,
            second_confidence=0.0,
            margin=0.0,
            latency_ms=elapsed,
            blocked=False,
        )

    top = matches[0]
    route = top.name or "commerce"
    dist = float(top.distance) if top.distance is not None else 0.5
    conf = _dist_to_conf(top.distance)

    second_route: Optional[str] = None
    second_conf = 0.0
    if len(matches) > 1 and matches[1].name:
        second_route = matches[1].name
        second_conf = _dist_to_conf(matches[1].distance)

    margin = conf - second_conf

    thresh = float(config.GUARD_BLOCK_MIN_CONFIDENCE)
    blocked = route in BLOCKING_ROUTES and conf >= thresh

    return GuardClassification(
        route=route,
        confidence=conf,
        distance=dist,
        second_route=second_route,
        second_confidence=second_conf,
        margin=margin,
        latency_ms=elapsed,
        blocked=blocked,
    )


def guard_result_dict(gc: GuardClassification) -> Dict[str, Any]:
    return {
        "guard_route": gc.route,
        "guard_confidence": round(gc.confidence, 4),
        "guard_distance": round(gc.distance, 4),
        "guard_second_route": gc.second_route,
        "guard_second_confidence": round(gc.second_confidence, 4) if gc.second_route else None,
        "guard_margin": round(gc.margin, 4),
        "guard_latency_ms": gc.latency_ms,
        "guard_blocked": gc.blocked,
    }


def empty_guard_dict() -> Dict[str, Any]:
    return {
        "guard_route": None,
        "guard_confidence": None,
        "guard_distance": None,
        "guard_second_route": None,
        "guard_second_confidence": None,
        "guard_margin": None,
        "guard_latency_ms": None,
        "guard_blocked": False,
    }
