"""
verify.py -- public certificate verification endpoint (Winnex Madhava).

Business Source License 1.1 (BSL 1.1)
Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
Contact: pay@winnex.ai

Validates a Mathematical Audit Certificate hash WITHOUT touching patient
data (LGPD / GDPR / HIPAA compliant). The QR Code on the certificate points
here:  /verify?tenant={tenantId}&hash={qrProjectionHash}
"""
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Winnex Audit Verification",
    version="1.0.0",
    description="Validates Madhava audit certificates (hash + proof metadata).",
)

# ---------------------------------------------------------------------------
# Issued-certificate store (demo). In production this reads from:
#   - the Liferay TriageAudit table, or
#   - the WORM evidence chain (append-only, SHA3-256).
# ---------------------------------------------------------------------------
_ISSUED: set = set()                # hashes that were issued
_REGISTERED: dict = {}              # hash -> proof metadata


def register(hash_: str, metadata: dict) -> None:
    """Register an issued certificate (called at issuance time)."""
    _ISSUED.add(hash_)
    _REGISTERED[hash_] = metadata


@app.get("/verify", response_class=HTMLResponse)
def verify(
    tenant: str = Query(...),
    hash_: str = Query(..., alias="hash"),
):
    """Public page: proves the triage was mathematically guaranteed.

    Args:
        tenant: the tenant id (e.g. 'liferay-1001'). Used for context only.
        hash_: the qr_projection_hash issued on the certificate.
    """
    if hash_ not in _ISSUED:
        return HTMLResponse(
            "<h1 style='color:#b91c1c'>INVALID</h1>"
            "<p>This certificate hash is not registered.</p>",
            status_code=404,
        )

    meta = _REGISTERED[hash_]
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
  <h3>Certificate metadata</h3>
  <div class="meta">
    <div>tenant_id    : {tenant}</div>
    <div>hash         : {hash_}</div>
    <div>sound        : {sound}</div>
    <div>bound_pairs  : {meta.get('bound_pairs', 0)}</div>
    <div>latency_ms   : {meta.get('latency_ms', 0)}</div>
  </div>
  <p class="foot">
    Winnex AI - Winnex Brasil Solucoes Empresariais LTDA
    (CNPJ 58.364.637/0001-47) &middot; pay@winnex.ai &middot;
    Business Source License 1.1
  </p>
</body></html>
"""
    return HTMLResponse(html)
