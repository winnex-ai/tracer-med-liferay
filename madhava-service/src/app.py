"""
Tracer-MED x Liferay -- Madhava Bridge Service
==============================================
HTTP service that exposes the `winnex-madhava` engine (C++20, v1.9.1) to
the Liferay OSGi bridge (winnex-madhava-service).

The engine contract (verified against the real package):
  - `winnex-madhava` depends ONLY on numpy (>=1.20). It does NOT embed text.
  - It accepts a float32 corpus directly (build_float32 path) and computes the
    Cauchy-Schwarz bound with per-document proof.
  - Endpoints expose index + search with bound_violations / bound_pairs / sound.

License: Business Source License 1.1 (BSL 1.1)
Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
Contact: pay@winnex.ai
"""
import logging
import os
import time
from typing import Any, Dict, List

import numpy as np

import winnex_madhava as wm

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("madhava-bridge")

app = FastAPI(
    title="Madhava Bridge (Tracer-MED x Liferay)",
    version="1.1.0",
    description="Cauchy-Schwarz proven vector search for Liferay Tracer-MED.",
    contact={"name": "Winnex AI | Klenio Padilha", "email": "pay@winnex.ai"},
)


# ---------------------------------------------------------------------------
# API Key authentication (security on the transport channel)
# ---------------------------------------------------------------------------
# In production, set MADHAVA_API_KEY in the environment (or a secret manager).
# All /v1/* endpoints REQUIRE the header:  X-Winnex-Api-Key: <key>
_API_KEY = os.environ.get("MADHAVA_API_KEY", "change-me-in-production")


def require_api_key(x_winnex_api_key: str = Header(default="", alias="X-Winnex-Api-Key")):
    """FastAPI dependency: rejects requests without the correct API key."""
    if not _API_KEY:
        return  # key disabled -> open (dev only)
    if not x_winnex_api_key or x_winnex_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
# Metrics / observability
# ---------------------------------------------------------------------------
_METRICS = {
    "total_requests": 0,
    "total_index_requests": 0,
    "total_search_requests": 0,
    "total_latency_ms": 0.0,
    "avg_latency_ms": 0.0,
    "total_bound_violations": 0,
    "total_bound_pairs": 0,
    "sound_requests": 0,
    "started_at": time.time(),
}


def _record_search(latency_ms: float, bound_violations: int, bound_pairs: int):
    m = _METRICS
    m["total_requests"] += 1
    m["total_search_requests"] += 1
    m["total_latency_ms"] += latency_ms
    m["total_bound_violations"] += bound_violations
    m["total_bound_pairs"] += bound_pairs
    if bound_violations == 0:
        m["sound_requests"] += 1
    m["avg_latency_ms"] = round(
        m["total_latency_ms"] / max(m["total_requests"], 1), 4)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class VectorDoc(BaseModel):
    """A document with its embedding vector (the engine's real input)."""
    vector: List[float]
    external_id: str = ""
    metadata: Dict[str, Any] = {}


class IndexRequest(BaseModel):
    corpus: List[VectorDoc]
    tenant_id: str = "default"
    stage1_dim: int = 64
    stage2_dim: int = 128
    k: int = 10


class SearchRequest(BaseModel):
    query: List[float]
    k: int = 10
    metadata_filter: Dict[str, Any] = {}
    tenant_id: str = "default"


# ---------------------------------------------------------------------------
# State (in-memory; production: persist per tenant)
# ---------------------------------------------------------------------------
_engines: Dict[str, Any] = {}
_corpora: Dict[str, List[VectorDoc]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/v1/health")
def health():
    return {
        "status": "ok",
        "engine": "winnex-madhava " + getattr(wm, "__version__", "?"),
        "tenants": list(_engines.keys()),
        "timestamp": time.time(),
    }


@app.get("/v1/stats")
def stats(_: str = Depends(require_api_key)):
    """Simple metrics endpoint for monitoring (Prometheus/health scripts)."""
    m = dict(_METRICS)
    m["uptime_s"] = round(time.time() - m["started_at"], 1)
    m["tenants"] = list(_engines.keys())
    return m


@app.post("/v1/index", dependencies=[Depends(require_api_key)])
def index(req: IndexRequest):
    if not req.corpus:
        raise HTTPException(422, "corpus must be non-empty")
    _METRICS["total_requests"] += 1
    _METRICS["total_index_requests"] += 1

    dim = len(req.corpus[0].vector)
    X = np.ascontiguousarray(
        np.array([d.vector for d in req.corpus], dtype=np.float32))

    if X.shape[1] != dim:
        raise HTTPException(422, "inconsistent vector dimensions")

    engine = wm.build_engine(
        X,
        dim=dim,
        metric="cosine",
        quant="int8",
        stage1_dim=min(req.stage1_dim, dim),
        stage2_dim=min(req.stage2_dim, dim),
        k=req.k,
        k1_fraction=0.05,
        modulation=True,
        postfilter=True,
        normalize_input=True,
        early_exit=False,
    )

    _engines[req.tenant_id] = engine
    _corpora[req.tenant_id] = req.corpus

    logger.info(
        "indexed %d docs for tenant %s (dim %d)",
        len(req.corpus), req.tenant_id, dim)

    return {
        "tenant_id": req.tenant_id,
        "indexed": len(req.corpus),
        "dim": dim,
        "engine": "winnex-madhava " + getattr(wm, "__version__", "?"),
    }


@app.post("/v1/search", dependencies=[Depends(require_api_key)])
def search(req: SearchRequest):
    if req.tenant_id not in _engines:
        raise HTTPException(
            404, f"tenant {req.tenant_id} not indexed -- POST /v1/index first")

    engine = _engines[req.tenant_id]
    corpus = _corpora[req.tenant_id]

    q = np.ascontiguousarray(np.array(req.query, dtype=np.float32))

    t0 = time.time()
    # Use the motor's witness audit (winnex-madhava >= 1.9.1) so the response
    # carries the per-document Cauchy-Schwarz certificate — the proof that
    # every excluded doc is mathematically outside the exact top-K. The
    # certificate is the motor's own pruning decision (captured at decision
    # time), not a recomputed one.
    if hasattr(engine, "search_audited"):
        ar = engine.search_audited(q, k=req.k, max_audit_records=500)
        r = type("R", (), {
            "indices": ar["indices"],
            "bound_violations": ar["bound_violations"],
            "bound_pairs": ar["bound_pairs"],
            "k1": None, "k2": None, "k3": None,
            "audit_excluded": ar["audit_excluded"],
            "audit": ar["audit"],
        })()
    else:
        r = engine.search(q)
        r.audit_excluded = 0
        r.audit = []
    latency_ms = (time.time() - t0) * 1000

    results = []
    for idx in r.indices:
        doc = corpus[int(idx)]
        results.append({
            "external_id": doc.external_id,
            "text_preview": (
                str(doc.metadata.get("text", ""))[:120]
                if isinstance(doc.metadata, dict) else ""),
            "metadata": doc.metadata,
            "index": int(idx),
        })

    _record_search(latency_ms, int(r.bound_violations), int(r.bound_pairs))

    return {
        "results": results,
        "bound_violations": int(r.bound_violations),
        "bound_pairs": int(r.bound_pairs),
        "k1": int(r.k1) if r.k1 is not None else None,
        "k2": int(r.k2) if r.k2 is not None else None,
        "k3": int(r.k3) if r.k3 is not None else None,
        "sound": int(r.bound_violations) == 0,
        "audit_excluded": int(r.audit_excluded),
        # The per-document mathematical certificate (winnex-madhava >= 1.9.1).
        "audit": [
            {
                "doc_id": int(rec["doc_id"]),
                "true_cosine": float(rec["true_cosine"]),
                "projected_cosine": float(rec["projected_cosine"]),
                "residual_norm": float(rec["residual_norm"]),
                "upper_bound": float(rec["upper_bound"]),
                "threshold": float(rec["threshold"]),
                "excluded": bool(rec["excluded"]),
                "stage": str(rec["stage"]),
            }
            for rec in r.audit
        ],
        "engine": "winnex-madhava " + getattr(wm, "__version__", "?"),
        "latency_ms": round(latency_ms, 3),
        "tenant_id": req.tenant_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
