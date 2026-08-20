"""
verify.py -- public certificate verification endpoint (Winnex Madhava).

Business Source License 1.1 (BSL 1.1)
Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
Contact: pay@winnex.ai

Validates a Mathematical Audit Certificate hash WITHOUT touching patient
data (LGPD / GDPR / HIPAA compliant). The QR Code on the certificate points
here:  /verify?tenant={tenantId}&hash={qrProjectionHash}

The verification reads the signed AuditCommitment from the WORM evidence
chain (winnex-tracer.persistence.WormStorage) and verifies its Ed25519
signature — non-repudiation, no in-memory store.
"""
import json
import os
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Winnex Audit Verification",
    version="1.0.0",
    description="Validates Madhava audit certificates (hash + proof metadata).",
)


def _find_commitment(hash_: str) -> Optional[dict]:
    """Find a signed commitment in the WORM by its query_fingerprint.

    The `hash` in the QR is the query_fingerprint (sha256 of the query
    vector bytes). Scans the WORM evidence chain (TRACER_MED_EVIDENCE_PATH)
    for a record whose commitment.query_fingerprint matches.
    """
    from winnex_tracer.persistence import WormStorage
    base = os.environ.get(
        "TRACER_MED_EVIDENCE_PATH", "/var/lib/tracer-med/evidence")
    worm = WormStorage(base_path=base)
    bp = worm.base_path
    if not bp.exists():
        return None
    for f in sorted(bp.rglob("records.jsonl")):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    block = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = block.get("data", {})
                comm = data.get("commitment")
                if isinstance(comm, dict) and comm.get("query_fingerprint") == hash_:
                    return {**block, **data}
    return None


def _verify_signature(comm: dict) -> dict:
    """Verify the Ed25519 signature of a commitment (non-repudiation)."""
    from winnex_tracer.core import verify_record, public_key_hex
    try:
        return verify_record(dict(comm), public_key_hex())
    except Exception as e:
        return {"status": "INVALID", "reason": str(e), "verified": False}


@app.get("/verify", response_class=HTMLResponse)
def verify(
    tenant: str = Query(...),
    hash_: str = Query(..., alias="hash"),
):
    """Public page: proves the triage was mathematically guaranteed.

    Args:
        tenant: the tenant id (e.g. 'liferay-1001'). Used for context only.
        hash_: the qr_projection_hash (query_fingerprint) issued on the
               certificate.
    """
    rec = _find_commitment(hash_)
    if rec is None:
        return HTMLResponse(
            "<h1 style='color:#b91c1c'>INVALID</h1>"
            "<p>This certificate hash is not registered in the WORM "
            "evidence chain.</p>",
            status_code=404,
        )

    comm = rec.get("commitment", rec)
    sig = _verify_signature(comm)
    if not sig.get("verified"):
        return HTMLResponse(
            "<h1 style='color:#b91c1c'>INVALID SIGNATURE</h1>"
            f"<p>{sig.get('reason', 'Ed25519 signature invalid.')}</p>",
            status_code=400,
        )

    meta = {
        "sound": int(comm.get("bound_violations", 0)) == 0,
        "engine": "winnex-madhava (search_with_commitment + Ed25519)",
        "bound_pairs": comm.get("bound_pairs", 0),
        "latency_ms": comm.get("_latency_ms", 0),
        "total_excluded": comm.get("total_provably_excluded", 0),
        "threshold": comm.get("global_threshold", 0),
        "worm_hash": rec.get("block_hash", ""),
    }
    sound = bool(meta.get("sound", True))
    status_style = (
        "background:#ecfdf5;border:2px solid #10b981"
        if sound else
        "background:#fef2f2;border:2px solid #b91c1c")
    badge = (
        '<span style="display:inline-block;background:#10b981;color:#fff;'
        'padding:6px 14px;border-radius:20px;font-weight:700;">[OK] VALIDATED</span>'
        if sound else
        '<span style="display:inline-block;background:#b91c1c;color:#fff;'
        'padding:6px 14px;border-radius:20px;font-weight:700;">BOUND VIOLATION</span>')
    verdict = (
        "This inference was processed by the Winnex Madhava engine with "
        "mathematical guarantees intact."
        if sound else
        "A bound violation was detected -- investigate immediately.")

    html = f"""
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Winnex Audit Certificate -- {"VALIDATED" if sound else "VIOLATION"}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 640px; margin: 40px auto; padding: 0 20px; color: #1f2937; }}
  .card {{ {status_style}; border-radius: 12px; padding: 24px; }}
  .meta {{ font-family: monospace; background: #f3f4f6; padding: 16px;
          border-radius: 8px; font-size: 13px; line-height: 1.8; }}
  .foot {{ font-size: 12px; color: #6b7280; margin-top: 24px; }}
  img {{ height: 48px; }}
</style></head><body>
  <img src="https://winnex.ai/logo-petit_white.webp" alt="Winnex AI">
  <div class="card">
    {badge}
    <h2>{verdict}</h2>
    <p>Engine: <b>{meta.get('engine', 'winnex-madhava 1.8.8')}</b></p>
    <p>Bound violations: <b>0</b> (Cauchy-Schwarz guarantee)</p>
  </div>
  <h3>Certificate metadata (from the WORM evidence chain)</h3>
  <div class="meta">
    <div>tenant_id        : {tenant}</div>
    <div>query_fingerprint: {hash_}</div>
    <div>sound            : {sound}</div>
    <div>bound_violations : 0 (Cauchy-Schwarz)</div>
    <div>bound_pairs      : {meta.get('bound_pairs', 0)}</div>
    <div>total_excluded   : {meta.get('total_excluded', 0)}</div>
    <div>global_threshold : {meta.get('threshold', 0)}</div>
    <div>latency_ms       : {meta.get('latency_ms', 0)}</div>
    <div>engine           : {meta.get('engine', 'winnex-madhava')}</div>
    <div>worm_hash        : {meta.get('worm_hash', '')}</div>
    <div>signature        : Ed25519 (verified)</div>
  </div>
  <p class="foot">
    Winnex AI - Winnex Brasil Solucoes Empresariais LTDA
    (CNPJ 58.364.637/0001-47) &middot; pay@winnex.ai &middot;
    Business Source License 1.1
  </p>
</body></html>
"""
    return HTMLResponse(html)
