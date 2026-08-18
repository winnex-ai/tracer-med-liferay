# Tracer-MED for Liferay -- Real Usage Examples

**Winnex AI | Klenio Padilha**
Winnex Brasil Solucoes Empresariais LTDA -- CNPJ 58.364.637/0001-47
Contact: **pay@winnex.ai** | Website: **https://winnex.ai**
License: **Business Source License 1.1 (BSL 1.1)**

![Winnex AI Logo](https://winnex.ai/logo-petit_white.webp)

---

## About these examples

Each example is a **complete, real implementation** you can drop into your own
Liferay DXP/Portal project. They all consume the **Madhava engine** (via the
`winnex-madhava-api` OSGi service and/or the `madhava-service` microservice)
to perform **soundness-guaranteed clinical retrieval**.

> **The pattern in one sentence:** a Liferay module does
> `@Reference MadhavaService`, calls `search(request)`, and receives results
> **with a mathematical proof** (`bound_violations`, `bound_pairs`, `sound`).

---

## Index of examples

| # | Example | What it demonstrates | Difficulty |
|---|---|---|---|
| [01](01-portlet-semantic-search/README.md) | **Portlet: Semantic Clinical Search** | A complete Portlet MVC that searches clinical records with proof, filterable by ICD-10 and department. The production pattern. | Medium |
| [02](02-rest-resource/README.md) | **REST: JAX-RS Resource** | Exposes `/o/rest/tracer-med/*` so any external system (or front-end) can search with proof over HTTP. | Medium |
| [03](03-scheduler/README.md) | **Scheduler: Auto-Index Worker** | A scheduled component (`@Component(immediate=true)`) that periodically re-indexes a tenant's corpus into Madhava. | Advanced |
| [04](04-service-builder/README.md) | **Service Builder: Audit Persistence** | Persists every triage (query, proof, results) in the Liferay database for long-term auditability. | Advanced |
| [05](05-standalone-client/README.md) | **Standalone: Direct HTTP Client** | A plain Java client (no Liferay) that talks to the `madhava-service` microservice -- useful for scripts, batch, or testing. | Basic |
| [07](07-qr-certificate/README.md) | **QR-Code Audit Certificate** | The "killer feature": a scannable Mathematical Audit Certificate (Winnex logo + CNPJ + QR projection hash + QR Code to `/verify`). | Medium |
| [scripts](scripts/README.md) | **Shell: cURL end-to-end** | Shell scripts to index a corpus and search with proof via the microservice -- the fastest way to see the math working. | Basic |

---

## The common data model

Every example uses the same DTOs from `winnex-madhava-api`:

```java
// A search request
MadhavaSearchRequest request = new MadhavaSearchRequest();
request.setQuery("hypertension management");
request.setK(10);
request.setTenantId("liferay-1001");        // tenant from the Liferay company
request.setCid10("I10");                     // optional ICD-10 filter
request.setDepartment("Cardiology");         // optional department filter

// A search response WITH PROOF
MadhavaSearchResponse response = madhavaService.search(request);

response.getBoundViolations();   // must be 0 -> nothing relevant lost
response.getBoundPairs();        // number of (document, bound) evaluations
response.isSound();              // true <-> bound_violations == 0
response.getResults();           // List<MadhavaDocument> with metadata
```

---

## Before you run the examples

1. The `madhava-service` microservice must be running (port 8600).
2. The `winnex-madhava-api` and `winnex-madhava-service` OSGi bundles must be
   deployed and ACTIVE in Liferay.
3. A corpus must be indexed for the target tenant (see
   [scripts](scripts/README.md)).

```bash
# Start everything
docker compose -f ../liferay/docker-compose.yml up -d

# Verify the engine
curl -s http://localhost:8600/v1/health
# {"status":"ok","engine":"winnex-madhava 1.8.8",...}
```

---

## The "why" behind each pattern

- **Portlet (01)** -- the UI face. Best for clinicians browsing records.
- **REST (02)** -- the API face. Best for integrations, mobile, or a front-end
  SPA calling Liferay.
- **Scheduler (03)** -- keeps the Madhava index fresh without human action.
- **Service Builder (04)** -- turns "we searched" into a durable, queryable
  audit record.
- **Standalone client (05)** -- the minimal contract, ideal to understand the
  microservice API and to script.

You can combine them freely: a hospital portal uses 01 + 03; an auditor uses
04; a lab integration uses 02.

---

## Legal reminder

All examples are **Business Source License 1.1 (BSL 1.1)** -- source-available.
Free for study, research, and Brazilian government agencies. Commercial use
requires a license from **Winnex AI** (`pay@winnex.ai`). After **2036-01-01**
the license converts to GPL v2.0+.

**Tracer-MED is not a medical device** and compliance reports are
self-assessment templates, not certifications.

---

*Winnex AI -- "Replace probability with proof, in the service of health."*
*BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
