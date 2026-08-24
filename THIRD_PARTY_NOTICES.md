# Tracer-MED for Liferay — Third-Party Notices

This file lists the third-party software and open-source components that the
Tracer-MED Product depends on or distributes, in accordance with the Liferay
Marketplace Developer Agreement §5.7 and applicable open-source licenses.
Winnex complies with all applicable open-source licenses.

**Product:** Tracer-MED for Liferay (OSGi portlets + FastAPI bridge service)
**Copyright:** © 2026 Winnex Brasil Solucoes Empresariais LTDA (BSL 1.1)

---

## OSGi bundles (distributed in the .lpkg)

The .lpkg distributes Winnex OSGi bundles (BSL 1.1). No third-party OSGi
bundles are embedded in the .lpkg; the portlets `@Reference` Liferay's
`release.portal.api` (compile-time only, not redistributed).

---

## Python runtime dependencies (FastAPI bridge service)

The `madhava-service` FastAPI service installs the following packages from
PyPI. They are **not** embedded in the .lpkg — they are installed in the
deployment environment via `requirements.txt`. Their licenses apply to their
own code:

| Package | License | Used for |
|---|---|---|
| `numpy` | BSD-3-Clause | Vector math (float32 engine input) |
| `fastapi` | MIT | HTTP API framework |
| `uvicorn` | BSD-3-Clause | ASGI server |
| `pydantic` | MIT | Request/response models |
| `pynacl` | Apache-2.0 | Ed25519 signing (non-repudiation) |
| `httpx` | BSD-3-Clause | HTTP client (embedding service calls) |
| `starlette` | BSD-3-Clause | ASGI framework (FastAPI dependency) |
| `sentence-transformers` | Apache-2.0 | Local text embedding (optional clinical models) |
| `winnex-madhava` | BSL 1.1 (Winnex) | C++20 vector-search engine |
| `winnex-ai-normalize` | BSL 1.1 (Winnex) | Text → embedding normalization |
| `winnex-tracer` | BSL 1.1 (Winnex) | WORM, commitment, med domain |

**Attribution:** The above open-source packages are used under their
respective licenses. The full license texts are available at the standard
license URLs (e.g., https://opensource.org/licenses/BSD-3-Clause,
https://opensource.org/licenses/MIT, https://www.apache.org/licenses/LICENSE-2.0)
and in each package's distribution.

---

## No source-code obligation

Tracer-MED is proprietary (BSL 1.1). It does not use any open-source license
that would require Winnex to license Tracer-MED's proprietary code under an
open-source license, nor does it cause End Users' proprietary technology to
become subject to an open-source license.

---

For questions about this notice or the licenses, contact **pay@winnex.ai**.
