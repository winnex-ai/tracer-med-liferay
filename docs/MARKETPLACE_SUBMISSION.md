# Marketplace Submission Guide - Tracer-MED for Liferay

**Winnex AI | Klenio Padilha**
Winnex Brasil Solucoes Empresariais LTDA - CNPJ 58.364.637/0001-47
Contact: **pay@winnex.ai** | Website: **https://winnex.ai**
License: **Business Source License 1.1 (BSL 1.1)**

![Winnex AI Logo](https://winnex.ai/logo-petit_white.webp)

> This guide prepares everything a seller needs to publish **Tracer-MED** on
> the **Liferay Marketplace**. The final submission is done through the
> Marketplace seller portal (web UI) - there is no public submission API.

---

## 1. What to submit

| Item | Path | Ready? |
|---|---|---|
| **Distribution package (.lpkg)** | `dist/tracer-med-1.0.0.lpkg` | YES (validated) |
| **Marketplace metadata** | embedded in the .lpkg | YES |
| **License file (BSL 1.1)** | `LICENSE` (inside the .lpkg) | YES |
| **End User License Agreement** | `EULA.md` (inside the .lpkg) | YES |
| **Third-party notices** | `THIRD_PARTY_NOTICES.md` (inside the .lpkg) | YES |
| **Logo** | `https://winnex.ai/logo-petit_white.webp` | YES |
| **Screenshots** | `docs/screenshots/*.png` | YES |
| **Source repository** | `https://github.com/winnex-ai/tracer-med-liferay` | YES (published) |

---

## 2. Package contents (verified)

The `.lpkg` contains exactly:

```
dist/tracer-med-1.0.0.lpkg
+-- LICENSE                          (BSL 1.1)
+-- EULA.md                          (Winnex Commercial EULA, worldwide)
+-- THIRD_PARTY_NOTICES.md           (OSS attribution)
+-- com.winnex.madhava.api-1.0.0.jar        (Bundle-SymbolicName com.winnex.madhava.api)
+-- com.winnex.madhava.service-1.0.0.jar    (Bundle-SymbolicName com.winnex.madhava.service)
+-- com.winnex.tracermed-1.0.0.jar          (Bundle-SymbolicName com.winnex.tracermed)
+-- liferay-marketplace.properties    (required-apps empty - self-contained)
```

- **ZIP integrity**: verified OK.
- **3 valid OSGi bundles**: verified (Bundle-SymbolicName / Bundle-Version present).
- **No internal docs, prompts, secrets, .env files, or dev-only bundles** in the package.

---

## 3. Marketplace listing metadata (ready to paste)

Use these values when creating the listing in the seller portal.

| Field | Value |
|---|---|
| **App name** | Tracer-MED |
| **Version** | 1.0.0 |
| **Short description** | Clinical triage with mathematical proof (Cauchy-Schwarz). Soundness-guaranteed retrieval for regulated healthcare. |
| **Long description** | Tracer-MED integrates the Winnex Madhava deterministic vector-search engine with Liferay DXP/Portal. Every search returns a per-document proof that no relevant clinical record was lost (0 bound violations). Multi-tenant by design (liferay-{companyId}), QR-code audit certificates, and LGPD/GDPR/HIPAA self-assessment reports. |
| **Category** | Clinical / Healthcare |
| **Tags** | clinical, triage, vector-search, proof, LGPD, HIPAA, GDPR, healthcare |
| **License** | Business Source License 1.1 (BSL 1.1) + Winnex Commercial EULA |
| **Price** | (choose: Free trial / Paid license) - commercial use requires a Winnex license |
| **Support URL** | https://winnex.ai |
| **Contact** | pay@winnex.ai |
| **Author / Vendor** | Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) |
| **Logo** | https://winnex.ai/logo-petit_white.webp |
| **Compatible with** | Liferay DXP 7.4.3.132+, Portal CE 7.4.3.132+ |
| **Requires JDK** | 11 or 17 |

---

## 4. Screenshots to upload

Use the captured screenshots from `docs/screenshots/`:

| File | Purpose |
|---|---|
| `01-home-guest.png` | Portal landing page |
| `02-login.png` | Login page |
| `04-home-authed.png` | Authenticated home |
| `05-portlet-render.png` | **The Tracer-MED portlet** (main product shot) |
| `06-control-panel.png` | Control panel / bundles |

> Best practice: upload at least 3 screenshots; the portlet render
> (`05-portlet-render.png`) should be the primary image.

---

## 5. Step-by-step submission (Marketplace seller portal)

The Liferay Marketplace submission is a **web UI workflow**. There is no public
API to upload an app programmatically.

### 5.1 Prerequisites

- A **seller account** on the Liferay Marketplace. If not registered yet:
  1. Go to https://www.liferay.com/marketplace
  2. Sign in (or create an account).
  3. Request **seller access** (Liferay reviews and approves vendor accounts).
- The `.lpkg` built and validated (`dist/tracer-med-1.0.0.lpkg`).

### 5.2 Create the app listing

1. Sign in to the **Marketplace seller portal**.
2. Navigate to **Developer / Publish** -> **Create New App**.
3. Fill the listing with the metadata from **section 3**.
4. Upload the screenshots from **section 4**.
5. Upload the `.lpkg` (`dist/tracer-med-1.0.0.lpkg`).

### 5.3 Configure the package

The Marketplace reads `liferay-marketplace.properties` inside the `.lpkg`.
Verify the values are present (they are):

```properties
app.version=1.0.0
app.marketplace=true
app.title=Tracer-MED - Clinical Triage with Mathematical Proof
app.owner=Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
app.license=Business Source License 1.1 (BSL 1.1)
app.contact=pay@winnex.ai
required-apps=
```

### 5.4 Submit for review

1. Click **Submit for Review**.
2. Liferay reviews the app (functionality, licensing, documentation).
3. On approval, the app is listed and available for installation from the
   Marketplace.

---

## 6. Troubleshooting the submission

| Symptom | Cause | Fix |
|---|---|---|
| "Invalid .lpkg" | File corrupted or missing bundles | Rebuild with `./scripts/build-lpkg.sh`; verify contents |
| "Required app missing" | `required-apps` references an external app | Keep `required-apps=` empty (this suite is self-contained) |
| "Bundle not found" | A JAR missing from the package | Confirm all 3 JARs are present (see section 2) |
| Submission rejected for license | BSL 1.1 must be stated | Confirm the LICENSE file and license field match |
| Cannot upload screenshots | Wrong format/size | Use PNG, under 2 MB each |

---

## 7. Post-publication checklist

- [ ] App visible in the Marketplace store.
- [ ] Installation works on a clean Liferay 7.4.3.132+ instance.
- [ ] Portlet appears under **Add -> Widgets -> Winnex**.
- [ ] The `madhava-service` container is documented as a prerequisite.
- [ ] Support email `pay@winnex.ai` is reachable.

---

## 8. Compliance checklist (Liferay Marketplace Developer Agreement)

| Agreement clause | Requirement | Where covered |
|---|---|---|
| §5.2 | Deliver in Liferay-prescribed format; no hidden functionality | This guide + .lpkg; dev-only bundles excluded |
| §5.5 | EULA with minimum clauses (a)–(e) | `EULA.md` Sections 1, 4, 5, 8, 9, 12, 14 |
| §5.5(a) | EULA between Developer and End User, not Liferay | `EULA.md` Section 1 |
| §5.5(b) | Liferay excluded from liability | `EULA.md` Section 4 |
| §5.5(c) | Non-embargo / US restricted parties representation | `EULA.md` Section 9 |
| §5.5(d) | Developer name + contact for claims | `EULA.md` Contact section |
| §5.5(e) | Liferay as intended third-party beneficiary | `EULA.md` Section 4 |
| §5.7 | OSS compliance + notices/offer for source | `THIRD_PARTY_NOTICES.md` |
| §9.1 | Privacy/healthcare data compliance | `EULA.md` Section 5 |
| §10 | Export compliance | `EULA.md` Section 9 |
| §12 | Representations and warranties | `EULA.md` Sections 8, 9 |
| §14 | Indemnification | `EULA.md` Sections 11, 12 |

---

## 9. Legal reminder

- **Business Source License 1.1** - source-available, not OSI open-source.
- Free for Brazilian government agencies (Additional Use Grant).
- Becomes GPL v2.0+ on **2036-01-01**.
- Commercial use requires a license agreement with Winnex AI.
- Tracer-MED is **not a medical device**; compliance reports are
  self-assessment templates.

---

*Winnex AI -- "Replace probability with proof, in the service of health."*
*BSL 1.1 | pay@winnex.ai | CNPJ 58.364.637/0001-47*
