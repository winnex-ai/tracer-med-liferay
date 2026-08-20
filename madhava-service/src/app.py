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
    # PRODUCTION path (winnex-tracer >= 1.0.0 + winnex-madhava >= 1.9.2):
    # the shared AuditCommitment — the motor returns a lightweight
    # count+threshold+boundary-sample, winnex_tracer.core signs it with
    # Ed25519 (make_worm_record), and the ~500-byte signed record is written
    # to the WORM evidence chain (TRACER_MED_EVIDENCE_PATH). No duplicated
    # commitment logic — it lives in the shared package.
    from winnex_tracer.core import make_worm_record
    from winnex_tracer.persistence import WormStorage

    if hasattr(engine, "search_with_commitment"):
        rec = make_worm_record(engine, q, k=req.k, max_sample=50,
                               query_vector_bytes=q.tobytes())
        r = type("R", (), {
            "indices": rec["indices"],
            "bound_violations": rec["bound_violations"],
            "bound_pairs": rec["bound_pairs"],
            "k1": None, "k2": None, "k3": None,
            "audit_excluded": rec["total_provably_excluded"],
            "audit": rec["sampled_records"],
            "commitment": rec,
        })()
        # Write the signed commitment to the WORM evidence chain.
        try:
            worm_path = os.environ.get(
                "TRACER_MED_EVIDENCE_PATH", "/var/lib/tracer-med/evidence")
            WormStorage(base_path=worm_path).append(
                {"commitment": rec, "_ctx": {"tenant_id": req.tenant_id}})
        except Exception as e:
            logger.warning("WORM evidence persist failed: %s", e)
    elif hasattr(engine, "search_audited"):
        ar = engine.search_audited(q, k=req.k, max_audit_records=500)
        r = type("R", (), {
            "indices": ar["indices"],
            "bound_violations": ar["bound_violations"],
            "bound_pairs": ar["bound_pairs"],
            "k1": None, "k2": None, "k3": None,
            "audit_excluded": ar["audit_excluded"],
            "audit": ar["audit"],
            "commitment": None,
        })()
    else:
        r = engine.search(q)
        r.audit_excluded = 0
        r.audit = []
        r.commitment = None
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

    # Normalize the audit records: the 1.9.2 commitment sample has
    # {doc_id, upper_bound, excluded}; the 1.9.1 certificate has the full
    # fields. Handle both.
    def _norm_audit_rec(rec):
        if "true_cosine" in rec:
            return {
                "doc_id": int(rec["doc_id"]),
                "true_cosine": float(rec["true_cosine"]),
                "projected_cosine": float(rec.get("projected_cosine", 0.0)),
                "residual_norm": float(rec.get("residual_norm", 0.0)),
                "upper_bound": float(rec["upper_bound"]),
                "threshold": float(rec["threshold"]),
                "excluded": bool(rec["excluded"]),
                "stage": str(rec.get("stage", "")),
            }
        return {
            "doc_id": int(rec["doc_id"]),
            "true_cosine": 0.0,
            "projected_cosine": 0.0,
            "residual_norm": 0.0,
            "upper_bound": float(rec.get("upper_bound", 0.0)),
            "threshold": float(getattr(r, "commitment", None)["global_threshold"])
                        if getattr(r, "commitment", None) else 0.0,
            "excluded": bool(rec.get("excluded", True)),
            "stage": "stage1",
        }

    return {
        "results": results,
        "bound_violations": int(r.bound_violations),
        "bound_pairs": int(r.bound_pairs),
        "k1": int(r.k1) if r.k1 is not None else None,
        "k2": int(r.k2) if r.k2 is not None else None,
        "k3": int(r.k3) if r.k3 is not None else None,
        "sound": int(r.bound_violations) == 0,
        "audit_excluded": int(r.audit_excluded),
        # The audit commitment (1.9.2+) or per-document certificate (1.9.1).
        "audit": [_norm_audit_rec(rec) for rec in r.audit],
        "commitment": getattr(r, "commitment", None),
        "engine": "winnex-madhava " + getattr(wm, "__version__", "?"),
        "latency_ms": round(latency_ms, 3),
        "tenant_id": req.tenant_id,
    }


# ---------------------------------------------------------------------------
# Normalization integration (winnex-ai-normalize) — provider registration
# and text → vector normalization, so the Liferay form can register embedding
# providers and any client can feed text to the Madhava engine.
# ---------------------------------------------------------------------------
class ProviderIn(BaseModel):
    name: str
    type: str = "openai_compat"
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    dim: int = 0
    timeout: float = 20.0
    priority: int = 10
    enabled: bool = True


class NormalizeRequest(BaseModel):
    input: List[str]
    model: str = ""


def _normalize_admin_required(authorization: str = Header(default="", alias="Authorization")):
    """Admin check for provider registration (fail-closed)."""
    from winnex_ai_normalize.core.provider_registry import require_admin_key
    try:
        require_admin_key(authorization)
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/v1/normalize/providers")
def list_providers(authorization: str = Header(default="", alias="Authorization")):
    """List registered embedding providers (secrets masked)."""
    _normalize_admin_required(authorization)
    from winnex_ai_normalize.core.provider_registry import get_registry
    return {"providers": get_registry().list()}


@app.post("/v1/normalize/providers")
def upsert_provider(provider: ProviderIn,
                    authorization: str = Header(default="", alias="Authorization")):
    """Register an embedding provider via the Liferay form (admin key)."""
    _normalize_admin_required(authorization)
    from winnex_ai_normalize.core.provider_registry import get_registry
    try:
        cfg = get_registry().upsert(provider.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"status": "registered", "provider": cfg.name}


@app.post("/v1/normalize/embed")
def normalize_embed(req: NormalizeRequest):
    """Text → float32 vectors (via the registered embedding provider).

    This is the plug that connects Liferay text input to the Madhava engine:
    the caller sends text, the normalizer embeds it with the configured
    provider (failover, no fake fallback), and returns Madhava-ready vectors.
    """
    from winnex_ai_normalize.core.embedding import get_embedding_service
    try:
        vecs = get_embedding_service().embed_texts(req.input)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return {
        "data": [
            {"embedding": vecs[i].tolist(), "index": i, "dim": int(vecs.shape[1])}
            for i in range(len(vecs))
        ],
        "model": req.model or "winnex-ai-normalize",
        "normalized": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
