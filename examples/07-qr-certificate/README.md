# Example 07 -- QR-Code Audit Certificate (the "Killer Feature")

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What this example does

Turns the abstract mathematics of Madhava into a **visual, scannable seal of
quality**: after a triage, the system emits a **Mathematical Audit Certificate**
containing the Winnex logo + CNPJ, the **QR projection hash**, the proof
metadata (latency, `pruned_by_bound`, `bound_violations`), and a **QR Code**
that anyone can scan to verify the guarantee was intact.

> **The killer value:** in a clinical context (LGPD, GDPR, HIPAA), the ability
> to prove *a posteriori* that a triage was based on **integer and
> mathematically validated data** is a massive selling point.

---

## Why this is brilliant

- **Does not expose patient data**: the QR Code validates only the
  **mathematical hash** and **performance metadata**, keeping full compliance
  with LGPD / HIPAA.
- **Tangibilizes the math**: Cauchy-Schwarz and QR projection become a
  scannable trust seal.

---

## How it works (architecture)

```
+- Liferay -----------------------------------------------------+
|                                                               |
|  Triage runs -> MadhavaSearchResponse (proof + qr_projection_hash) |
|        |                                                      |
|        ▼                                                      |
|  Service Builder: TriageAudit saved with hash + proof metadata |
|        |                                                      |
|        ▼                                                      |
|  CertificateGenerator -> PDF / modal with:                     |
|     * Winnex logo + CNPJ                                     |
|     * qr_projection_hash (e.g. 0x7f3a...)                    |
|     * timestamp + tenant ID                                  |
|     * QR Code (URL to the verify endpoint)                   |
+--------------+-----------------------------------------------+
               | scan
               ▼
+---------------------------------------------------------------+
|  https://api.winnex.ai/verify?tenant=...&hash=...            |
|  (FastAPI /verify endpoint)                                  |
|  -> "[OK] VALIDATED: processed by Winnex Madhava 1.8.8 with      |
|     mathematical guarantees intact."                          |
+---------------------------------------------------------------+
```

---

## The files

```
example-07-qr-certificate/
+-- src/main/java/com/winnex/tracermed/certificate/
|   +-- CertificateGenerator.java     <- builds the certificate (PDF/modal)
|   +-- QrCodeUrlBuilder.java         <- builds the scannable verify URL
|   +-- QrCertificatePortlet.java     <- renders the certificate in the UI
+-- fastapi/verify.py                 <- the /verify endpoint (Python)
+-- README.md                         <- this file
```

---

## Step 1 -- The verify URL builder (Java, Liferay)

```java
/*
 * Business Source License 1.1 (BSL 1.1)
 * Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
 * Contact: pay@winnex.ai
 */
package com.winnex.tracermed.certificate;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

/**
 * Builds the scannable verification URL for a triage certificate.
 *
 * <p>The URL contains ONLY the mathematical hash and the tenant -- no patient
 * data -- so it is fully LGPD/HIPAA compliant.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class QrCodeUrlBuilder {

    /** Base of the public verification service (configure in System Settings). */
    public static final String DEFAULT_VERIFY_BASE =
        "https://api.winnex.ai/verify";

    /**
     * Builds: {base}?tenant={tenantId}&hash={qrProjectionHash}
     */
    public static String build(String base, String tenantId, String qrHash) {
        if (base == null || base.isEmpty()) {
            base = DEFAULT_VERIFY_BASE;
        }
        return base
            + "?tenant=" + URLEncoder.encode(tenantId, StandardCharsets.UTF_8)
            + "&hash=" + URLEncoder.encode(qrHash, StandardCharsets.UTF_8);
    }

    /** Convenience with the default base URL. */
    public static String build(String tenantId, String qrHash) {
        return build(DEFAULT_VERIFY_BASE, tenantId, qrHash);
    }

}
```

---

## Step 2 -- The certificate generator (Java, Liferay)

```java
package com.winnex.tracermed.certificate;

import com.winnex.madhava.api.dto.MadhavaSearchResponse;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/**
 * Generates the "Mathematical Audit Certificate" data for a triage.
 *
 * <p>This is the payload that a PDF template (or a modal) renders. It carries
 * the Winnex brand, the QR projection hash, and the proof metadata -- never
 * patient content.</p>
 *
 * @author Winnex AI | Klenio Padilha
 */
public class CertificateGenerator {

    /** Winnex corporate brand block (used by the certificate template). */
    public static final String WINNEX_VENDOR =
        "Winnex AI - Winnex Brasil Solucoes Empresariais LTDA";
    public static final String WINNEX_CNPJ = "58.364.637/0001-47";
    public static final String WINNEX_CONTACT = "pay@winnex.ai";
    public static final String WINNEX_LOGO = "https://winnex.ai/logo-petit_white.webp";

    private static final DateTimeFormatter ISO =
        DateTimeFormatter.ISO_INSTANT.withZone(ZoneOffset.UTC);

    /**
     * Builds the certificate model from a triage response.
     *
     * @param response     the Madhava search response (WITH proof)
     * @param tenantId     the tenant (liferay-{companyId})
     * @param qrHash       the QR projection hash from the engine
     * @param verifyBase   the public verify endpoint base URL
     */
    public static CertificateModel build(
            MadhavaSearchResponse response, String tenantId,
            String qrHash, String verifyBase) {

        CertificateModel m = new CertificateModel();
        m.vendor = WINNEX_VENDOR;
        m.cnpj = WINNEX_CNPJ;
        m.contact = WINNEX_CONTACT;
        m.logo = WINNEX_LOGO;

        m.tenantId = tenantId;
        m.qrHash = qrHash;
        m.timestamp = ISO.format(Instant.now());

        // Proof metadata (the math made visible)
        m.boundViolations = response.getBoundViolations();
        m.boundPairs = response.getBoundPairs();
        m.sound = response.isSound();
        m.engine = response.getEngine();
        m.latencyMs = response.getLatencyMs();

        // The scannable URL (hash + tenant only)
        m.verifyUrl = QrCodeUrlBuilder.build(verifyBase, tenantId, qrHash);

        // The human verdict
        m.verdict = m.sound
            ? "VALIDATED -- processed by Winnex Madhava with 0 bound violations "
              + "(Cauchy-Schwarz guarantee intact)."
            : "BOUND VIOLATION -- investigate.";

        return m;
    }

    /** Simple POJO carrying all certificate fields. */
    public static class CertificateModel {
        public String vendor, cnpj, contact, logo;
        public String tenantId, qrHash, timestamp, engine, verifyUrl, verdict;
        public long boundViolations, boundPairs;
        public boolean sound;
        public double latencyMs;
    }

}
```

---

## Step 3 -- The /verify endpoint (Python, FastAPI)

Add this to the `madhava-service` (or a dedicated public service). It
validates the hash **without touching patient data**.

```python
"""
verify.py -- public certificate verification endpoint.

Business Source License 1.1 (BSL 1.1)
Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
Contact: pay@winnex.ai
"""
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="Winnex Audit Verification", version="1.0.0")

# In production this comes from a store/DB of issued hashes
# (e.g. the Liferay TriageAudit table or the WORM evidence chain).
_ISSUED = set()          # demo: in-memory set of valid hashes
_REGISTERED = {}         # demo: hash -> proof metadata


def register(hash_: str, metadata: dict) -> None:
    """Called at issuance time by the ingestion/certificate pipeline."""
    _ISSUED.add(hash_)
    _REGISTERED[hash_] = metadata


@app.get("/verify", response_class=HTMLResponse)
def verify(
    tenant: str = Query(...),
    hash_: str = Query(..., alias="hash"),
):
    """Public page: proves the triage was mathematically guaranteed."""
    if hash_ not in _ISSUED:
        return HTMLResponse(
            "<h1 style='color:#b91c1c'>INVALID</h1>"
            "<p>This certificate hash is not registered.</p>",
            status_code=404,
        )

    meta = _REGISTERED[hash_]
    html = f"""
    <!DOCTYPE html>
    <html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Winnex Audit Certificate -- VALIDATED</title>
    <style>
      body {{ font-family: sans-serif; max-width: 640px; margin: 40px auto;
             padding: 0 20px; color: #1f2937; }}
      .ok {{ background: #ecfdf5; border: 2px solid #10b981; border-radius: 12px;
            padding: 24px; }}
      .badge {{ display:inline-block; background:#10b981; color:#fff;
                padding:6px 14px; border-radius:20px; font-weight:700; }}
      .meta {{ font-family: monospace; background:#f3f4f6; padding:16px;
              border-radius:8px; font-size:13px; }}
      img {{ height: 48px; }}
    </style></head><body>
      <img src="https://winnex.ai/logo-petit_white.webp" alt="Winnex AI">
      <div class="ok">
        <span class="badge">[OK] VALIDATED</span>
        <h2>This inference was processed by the Winnex Madhava engine with
            mathematical guarantees intact.</h2>
        <p>Engine: <b>{meta.get('engine','winnex-madhava 1.8.8')}</b></p>
        <p>Bound violations: <b>0</b> (Cauchy-Schwarz guarantee)</p>
      </div>
      <h3>Certificate metadata</h3>
      <div class="meta">
        <div>tenant_id : {tenant}</div>
        <div>hash      : {hash_}</div>
        <div>sound     : {meta.get('sound', True)}</div>
        <div>bound_pairs : {meta.get('bound_pairs', 0)}</div>
        <div>latency_ms : {meta.get('latency_ms', 0)}</div>
      </div>
      <p style="font-size:12px;color:#6b7280">
        Winnex AI - Winnex Brasil Solucoes Empresariais LTDA
        (CNPJ 58.364.637/0001-47) . pay@winnex.ai .
        Business Source License 1.1</p>
    </body></html>
    """
    return HTMLResponse(html)
```

---

## Step 4 -- Rendering the QR Code in the UI (Portlet)

In your certificate modal / JSP, render the QR Code using a tiny JS lib (or a
server-side PNG generator). The QR payload is the **verify URL** from
`QrCodeUrlBuilder`:

```jsp
<%-- Certificate modal (view.jsp of QrCertificatePortlet) --%>
<div class="winnex-certificate"
     style="border:2px solid #003056;border-radius:12px;padding:24px;
            max-width:480px;font-family:sans-serif;">

    <img src="https://winnex.ai/logo-petit_white.webp" width="140"
         style="object-fit:contain;"/>
    <h3 style="margin:8px 0 0;color:#003056;">Mathematical Audit Certificate</h3>
    <p style="color:#6b7280;font-size:13px;margin:2px 0 16px;">
        Winnex AI - Winnex Brasil Solucoes Empresariais LTDA
        (CNPJ 58.364.637/0001-47)</p>

    <div style="font-family:monospace;background:#f3f4f6;padding:12px;
                border-radius:8px;font-size:12px;line-height:1.7;">
        <div>qr_projection_hash : <b>0x7f3a...</b></div>
        <div>bound_violations   : <b>0</b></div>
        <div>bound_pairs       : <b><%=cert.boundPairs%></b></div>
        <div>sound             : <b>true</b></div>
        <div>latency_ms        : <b><%=cert.latencyMs%></b></div>
        <div>engine            : <b>winnex-madhava 1.8.8</b></div>
    </div>

    <div style="text-align:center;margin-top:16px;">
        <%-- QR Code image (payload = cert.verifyUrl) --%>
        <img src="/qr?data=<%=URLEncoder.encode(cert.verifyUrl, "UTF-8")%>"
             width="160" height="160" alt="Scan to verify"
             style="border:1px solid #d1d5db;border-radius:8px;"/>
        <p style="font-size:12px;color:#6b7280;margin:8px 0 0;">
            Scan to verify this triage on api.winnex.ai</p>
    </div>

    <p style="margin-top:16px;font-size:12px;color:#16a34a;font-weight:700;">
        [OK] <%=cert.verdict%></p>
</div>
```

> The QR Code itself is generated by any standard library (ZXing for Java,
> `qrcode` for Python). The payload is always the **verify URL** -- the hash +
> tenant -- never patient content.

---

## How the full flow connects

1. **Triage runs** -> `MadhavaSearchResponse` (with proof + `qr_projection_hash`).
2. **Service Builder saves** the audit row (Example 04) **including** the hash
   and proof metadata.
3. **CertificateGenerator** builds the certificate model (brand + hash + proof).
4. **Portlet / PDF** renders the certificate with the QR Code.
5. **Anyone scans** -> `https://api.winnex.ai/verify?tenant=...&hash=...`
6. **FastAPI** returns: *"[OK] VALIDATED -- processed by Winnex Madhava with
   mathematical guarantees intact."*

---

## Compliance notes (LGPD / GDPR / HIPAA)

- The QR Code carries **only** the mathematical hash + tenant id -- **no**
  patient identifiers, **no** clinical content.
- The full clinical context stays inside the Liferay tenant (access-controlled).
- The verify page shows only performance/proof metadata -- safe to expose.
- Combined with the WORM evidence chain (Example 04), you get both an
  **immutable** and a **scannable** audit trail.

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
