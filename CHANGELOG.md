# Changelog

All notable changes to **Tracer-MED for Liferay** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**License:** Business Source License 1.1 (BSL 1.1)
**Contact:** pay@winnex.ai
**Author:** Winnex AI | Klenio Padilha

---

## [1.0.0] - 2026-08-18

### Added

- **Liferay integration** (3 OSGi bundles):
  - `winnex-madhava-api` - public `MadhavaService` interface + DTOs (the "pip").
  - `winnex-madhava-service` - HTTP implementation of the bridge to the
    Madhava microservice (configurable via System Settings).
  - `winnex-tracer-med` - Portlet MVC consumer that renders triage with proof.
- **Madhava microservice** (`madhava-service`, Python/FastAPI):
  - `POST /v1/index` - ingest a float32 corpus for a tenant.
  - `POST /v1/search` - search with Cauchy-Schwarz proof.
  - `GET /v1/health` - engine status.
- **Security on the transport channel**:
  - API Key authentication (`X-Winnex-Api-Key` header) enforced on `/v1/*`
    endpoints via FastAPI dependency.
  - Production note: use `https://` and set `MADHAVA_API_KEY`.
- **Metrics / observability**:
  - `GET /v1/stats` - `total_requests`, `avg_latency_ms`,
    `total_bound_violations`, `sound_requests`, uptime, tenants.
- **QR-Code audit certificate** (`examples/07-qr-certificate/`):
  - `CertificateGenerator` (Java) builds the certificate model.
  - `QrCodeUrlBuilder` builds the scannable verify URL.
  - `verify.py` (FastAPI) validates the hash and returns a clean page
    WITHOUT leaking vectors or patient data (only proof status, timestamp,
    tenant id).
- **Real usage examples** (`examples/`):
  - 01 Portlet semantic search
  - 02 REST JAX-RS resource
  - 03 Auto-index scheduler
  - 04 Service Builder audit persistence
  - 05 Standalone HTTP client
  - 07 QR-code certificate
  - scripts (cURL end-to-end)
- **Model integration guide** (`docs/MODEL_INTEGRATION_GUIDE.md`):
  - The Float32 contract.
  - Ingestion pipeline (legacy DB -> normalization -> `/v1/index`).
  - Interpretation of results (what `sound`, `bound_violations`,
    `pruned_by_bound` mean).
- **Documentation**:
  - User-oriented README with screen demos.
  - Installation plan, bridge study.

### Changed

- Madhava microservice version bumped to `1.1.0` (API key + metrics).

### Depends on

- `winnex-madhava` **1.8.8** (PyPI) - C++20 engine, numpy-only.
- Liferay **DXP/Portal 7.4.3.132+**.
- Python **3.12** (cp312 wheel for winnex-madhava).
- Docker + Docker Compose.

---

*Winnex AI -- "Replace probability with proof, in the service of health."*
*BSL 1.1 | pay@winnex.ai | CNPJ 58.364.637/0001-47*
