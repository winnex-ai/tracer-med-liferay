# Model Integration Guide -- From Clinical Data to Madhava

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

![Winnex AI Logo](https://winnex.ai/logo-petit_white.webp)

> **Purpose:** this guide teaches developers how to **prepare data** for the
> Madhava API. The examples in `examples/` show how Liferay calls the API; this
> guide shows how to transform *your* data into the **float32 vectors** the
> engine understands.

---

## 1. The Float32 Contract

### 1.1 The single most important rule

> **The Madhava engine does NOT process text or raw JSON. It processes
> normalized float32 tensors.**

`winnex-madhava` 1.8.8 depends **only on numpy**. It does not embed text. Its
input contract is:

- A 2D array of shape `(n_documents, dimension)` with dtype **float32**.
- Each row is one document's **embedding vector**.
- For `metric="cosine"` (the default), each vector is **L2-normalized to unit
  norm** at build time.

### 1.2 What this means for you

| Your data | What you must do |
|---|---|
| Free text (clinical notes, reports) | **Embed it** with an embedding model (BGE, BlueBERT, OpenAI, etc.) -> float32 vector |
| Structured numeric data (vitals, labs) | **Encode** into a vector of numeric features, then normalize |
| Categorical data (ICD-10, department) | **One-hot / embedding** into numeric features |
| Mixed data | Concatenate the encodings into one vector per document |

---

## 2. Working example -- vitals + diagnosis

### 2.1 Raw clinical record

```
Patient: PT-8f3a2c1b
Vitals:  temp=37.2 degC, bpm=85, spo2=98, systolic=150, diastolic=95
Diagnosis: I10 (Essential hypertension)
Department: Cardiology
Text: "Patient with essential hypertension, BP 150/95. ACE inhibitor therapy."
```

### 2.2 The encoding pipeline

```python
"""
Data preparation for Madhava -- from clinical records to float32 vectors.

Business Source License 1.1 (BSL 1.1)
Copyright (c) 2026 Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
Contact: pay@winnex.ai
"""
import numpy as np

# ---------------------------------------------------------------------------
# Option A: structured features (numeric vitals + categorical encodings)
# ---------------------------------------------------------------------------
def vitals_to_vector(temp, bpm, spo2, systolic, diastolic,
                     cid10_index, department_index, dims=(5, 10, 8)):
    """Build a mixed numeric/categorical vector for a clinical record."""
    n_vitals, n_cid, n_dept = dims

    v = np.zeros(n_vitals + n_cid + n_dept, dtype=np.float32)

    # Numeric vitals (clip + scale to roughly [0,1])
    v[0] = np.clip((temp - 35.0) / 5.0, 0, 1)          # 37.2 -> ~0.44
    v[1] = np.clip((bpm - 40.0) / 120.0, 0, 1)         # 85   -> ~0.375
    v[2] = np.clip((spo2 - 80.0) / 20.0, 0, 1)         # 98   -> ~0.90
    v[3] = np.clip((systolic - 80.0) / 100.0, 0, 1)    # 150  -> ~0.70
    v[4] = np.clip((diastolic - 50.0) / 80.0, 0, 1)    # 95   -> ~0.56

    # Categorical: one-hot ICD-10 (index from a fixed codebook)
    if 0 <= cid10_index < n_cid:
        v[n_vitals + cid10_index] = 1.0

    # Categorical: one-hot department (index from a fixed codebook)
    if 0 <= department_index < n_dept:
        v[n_vitals + n_cid + department_index] = 1.0

    return v

# ---------------------------------------------------------------------------
# Option B: text embedding (free-text clinical notes)
# ---------------------------------------------------------------------------
def text_to_vector(text, model):
    """Embed free text with any sentence/embedding model.

    NOTE: `model` is external (BGE, BlueBERT, OpenAI, etc.). Madhava itself
    does NOT embed -- this is your data-preparation step.
    """
    vec = model.encode([text], normalize_embeddings=True)  # (1, d) float32
    return vec[0].astype(np.float32)

# ---------------------------------------------------------------------------
# Putting it together: one document -> one vector
# ---------------------------------------------------------------------------
def record_to_vector(record, text_model, codebook):
    """Combine structured + text signals into the final document vector."""
    vitals = vitals_to_vector(
        temp=record["temp"], bpm=record["bpm"], spo2=record["spo2"],
        systolic=record["sys"], diastolic=record["dia"],
        cid10_index=codebook["cid10"][record["cid10"]],
        department_index=codebook["dept"][record["department"]])

    text = text_to_vector(record["text"], text_model)

    # Final vector = concatenation, then unit-normalized (cosine contract)
    vec = np.concatenate([vitals, text]).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 1e-10:
        vec = vec / norm

    return vec
```

### 2.3 Normalization is the key

For `metric="cosine"`, the engine L2-normalizes at build. But you should
**normalize yourself** to keep the projection residuals meaningful:

```python
vec = np.ascontiguousarray(vec, dtype=np.float32)
vec = vec / (np.linalg.norm(vec) + 1e-9)   # unit norm -> cosine space
```

> **Why:** the Cauchy-Schwarz residual `e(v) = sqrt(||v||² − ||Pv||²)`
> assumes unit-norm vectors. Normalizing keeps the bound tight and the proof
> meaningful.

---

## 3. The Ingestion Pipeline (the Scheduler's role)

### 3.1 The flow

```
+- Legacy database (SQL / FHIR / CSV) ---------------------------+
|   clinical_records: id, text, cid10, department, vitals        |
+--------------+-------------------------------------------------+
               |  Example 03 scheduler (adapted) runs on cron
               ▼
+- Normalization script (Python or Java) ------------------------+
|   for each row:                                                |
|     vec = record_to_vector(row, text_model, codebook)          |
|     doc  = {external_id, vector: vec.tolist(), metadata: {...}}|
+--------------+-------------------------------------------------+
               |  POST /v1/index  (build_float32 path in the engine)
               ▼
+- winnex-madhava (microservice) --------------------------------+
|   build_float32 -> projections -> Cauchy-Schwarz residuals       |
|   -> ready for soundness-guaranteed search                      |
+----------------------------------------------------------------+
```

### 3.2 Adapting Example 03 for a legacy DB

The scheduler's `CorpusLoader.load(tenantId)` is the only seam you change.
Instead of returning an empty corpus, query your legacy database and normalize:

```java
// CorpusLoader.load(tenantId) -- adapted for a legacy SQL database
public List<CorpusDocument> load(String tenantId) {
    List<CorpusDocument> docs = new ArrayList<>();

    // 1. Pull rows for this tenant/company
    //    SELECT id, text, cid10, department, temp, bpm, spo2
    //    FROM clinical_records WHERE company_id = ?
    List<Row> rows = legacyDao.fetchForCompany(tenantId);

    // 2. For each row, produce a normalized float32 vector
    for (Row r : rows) {
        float[] vec = normalizer.recordToVector(
            r.getText(), r.getCid10(), r.getDepartment(),
            r.getTemp(), r.getBpm(), r.getSpo2());

        docs.add(new CorpusDocument(
            r.getId(), r.getText(), toList(vec),
            r.getCid10(), r.getDepartment()));
    }

    // 3. Return -> the scheduler POSTs /v1/index
    return docs;
}
```

> The vector conversion can run in **Python** (easier ML tooling) or **Java**
> (same JVM as Liferay). Both produce the same JSON: `{"vector":[...], ...}`.

---

## 4. Interpreting the Results (what does "Sound" mean?)

### 4.1 The business-facing translation table

| Output field | Example | What it means for the business |
|---|---|---|
| `bound_violations: 0` | `0` | **The search is mathematically exact** within the defined tolerance -- no relevant record was lost. This is the guarantee. |
| `sound: true` | `true` | Same as above -- a convenience flag: `bound_violations == 0`. |
| `bound_pairs: 150` | `150` | The engine evaluated 150 `(document, bound)` pairs -- the audit record size of this query. |
| `pruned_by_bound: 120` | `120` | The C++ engine **safely discarded** 120 irrelevant records by proof, saving CPU time while preserving the guarantee. |
| `pruned_by_prefilter: 25` | `25` | 25 records were cut by the Stage-1 keep-fraction heuristic (a latency control, NOT a proof). |
| `exact_evals: 30` | `30` | 30 survivors were re-scored exactly by the post-filter -- the final ranking is exact. |
| `k1 / k2 / k3` | `8 / 8 / 8` | Cascade stage sizes (wide bound -> tight bound -> exact). At tiny scale they equal N -- a linear scan with proof. |
| `latency_ms: 3.99` | `3.99` | Wall-clock query latency. |
| `recall@10: 1.0` | `1.0` | Perfect recall vs the exact scan -- the engine found everything the exact scan would. |

### 4.2 The honest reading (important for product/sales)

- At the published scale (hundreds to a few thousand documents), `bound_pairs`
  equals `N × queries` -- a **linear scan with per-document proofs**. The
  benchmarks demonstrate **correctness and auditability**, not sublinear speed.
- `0 bound violations` is expected **by construction** (the bound is an
  inequality, and every document is evaluated).
- The **efficiency advantage** (pruning well below N) becomes real at
  million-scale corpora and with the **UB Width** mode (`basis="pca_corpus"`),
  where proof-based pruning reaches 95%+ at d=1536.

**The value proposition is NOT speed -- it is provability + auditability.**
That is what regulated markets (LGPD, AI Act, HIPAA) require.

---

## 5. Common integration questions

### Q1: My data is only text. What do I do?
Embed it with a model (BGE-small, BlueBERT, OpenAI Ada-002, etc.) -> float32
vector -> POST `/v1/index`. The engine then searches that vector space with the
proof.

### Q2: My data is only structured numbers (vitals, labs).
Encode into a numeric feature vector (see section 2.2), normalize to unit
norm, and index. The proof still applies -- similarity is defined in *your*
feature space.

### Q3: What dimension should my vectors be?
Any. The engine builds projections at `stage1_dim` (default 64) and
`stage2_dim` (default 128) internally; the corpus dimension is whatever your
embeddings produce (384 for BGE, 768 for BlueBERT, 1536 for OpenAI/Qwen).
For d ≥ 384, use `early_exit=False` (the safe default since v1.8.5) and
consider `basis="pca_corpus"` for tight bounds.

### Q4: Do I need a GPU?
No. The bound engine runs on CPU (AVX2/OpenMP). GPU is optional
(`speed=True`) for high-throughput batch.

### Q5: How do I map results back to my records?
`POST /v1/search` returns `external_id` per result -- the id you supplied at
index time. Use it to re-join with your database.

---

## 6. Checklist for integrating a new module

- [ ] Define the **feature space**: which fields -> which vector components.
- [ ] Pick the **embedding model** for free text (or a fixed numeric encoding).
- [ ] Write the **normalizer** that turns a record into a unit-norm float32 vector.
- [ ] Index via **Example 03** (scheduler) -> `POST /v1/index`.
- [ ] Search via **Example 01/02** -> `POST /v1/search`.
- [ ] Persist the audit (hash + proof) via **Example 04**.
- [ ] Emit the scannable certificate via **Example 07**.
- [ ] Verify: `bound_violations == 0` on every query.

---

*Winnex AI -- "Replace probability with proof, in the service of health."*
*Business Source License 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
