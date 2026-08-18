# Shell -- cURL End-to-End with the Madhava Microservice

**Winnex AI | Klenio Padilha** . Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47) . pay@winnex.ai . BSL 1.1

---

## What these scripts do

Give you the **fastest possible proof** that the Winnex Madhava engine is
working: index a small clinical corpus and search it, all via `curl`. No Java,
no Liferay -- just the microservice.

---

## The files

```
scripts/
+-- 01-index.sh      <- POST /v1/index (ingest a corpus)
+-- 02-search.sh     <- POST /v1/search (search with proof)
+-- 03-e2e.sh        <- health + index + search in one shot
```

---

## Step 1 -- `01-index.sh`

```bash
#!/usr/bin/env bash
# Index a small clinical corpus into the Madhava microservice.
# Usage: ./01-index.sh [base_url]   (default http://localhost:8600)
set -euo pipefail

BASE="${1:-http://localhost:8600}"

# A tiny 6-document corpus. NOTE: the Madhava engine does NOT embed text;
# the "vector" fields must come from an embedding model. Here we use 32
# random unit vectors as a stand-in so the script runs anywhere.
python3 - <<'PY' > /tmp/tracer-med-corpus.json
import json, math, random
random.seed(7)
def unit():
    v = [random.gauss(0,1) for _ in range(32)]
    n = math.sqrt(sum(x*x for x in v))
    return [round(x/n, 6) for x in v]

docs = [
    ("MTS-0001", "I10", "Patient with essential hypertension, BP 150/95. ACE inhibitor."),
    ("MTS-0002", "E11", "Type 2 diabetes mellitus. HbA1c 8.2%. Metformin."),
    ("MTS-0003", "I10", "Cardiac evaluation, ECG normal sinus rhythm."),
    ("MTS-0004", "E78", "Lipid panel. LDL 160. Recommend statin."),
    ("MTS-0005", "I10", "Hypertension management: ACE inhibitor first-line."),
    ("MTS-0006", "Z03", "Chest radiograph: normal silhouette, clear lungs."),
]
print(json.dumps({
    "tenant_id": "liferay-1001",
    "corpus": [
        {"external_id": eid, "vector": unit(),
         "metadata": {"cid10": cid, "text": txt}}
        for eid, cid, txt in docs
    ],
    "k": 5,
}))
PY

echo "== POST /v1/index =="
curl -s -X POST "$BASE/v1/index" \
  -H "Content-Type: application/json" \
  -d @/tmp/tracer-med-corpus.json | python3 -m json.tool
```

---

## Step 2 -- `02-search.sh`

```bash
#!/usr/bin/env bash
# Search the corpus with proof.
# Usage: ./02-search.sh [base_url]   (default http://localhost:8600)
set -euo pipefail

BASE="${1:-http://localhost:8600}"

# Build a query vector: document 0 ("hypertension") + light noise, so the
# expected top result is MTS-0001.
python3 - <<'PY' > /tmp/tracer-med-query.json
import json, math, random
random.seed(7)
def unit():
    v = [random.gauss(0,1) for _ in range(32)]
    n = math.sqrt(sum(x*x for x in v))
    return [round(x/n, 6) for x in v]

base = unit()
q = [base[j] + 0.1*random.gauss(0,1) for j in range(32)]
n = math.sqrt(sum(x*x for x in q))
q = [round(x/n, 6) for x in q]

print(json.dumps({"query": q, "tenant_id": "liferay-1001", "k": 3}))
PY

echo "== POST /v1/search =="
RESP=$(curl -s -X POST "$BASE/v1/search" \
  -H "Content-Type: application/json" \
  -d @/tmp/tracer-med-query.json)

echo "$RESP" | python3 -m json.tool

echo ""
echo "== reading the proof =="
if echo "$RESP" | grep -q '"bound_violations": 0'; then
  echo "SOUND: 0 bound violations -- no relevant record was lost."
else
  echo "BOUND VIOLATION -- investigate!"
fi
```

---

## Step 3 -- `03-e2e.sh` (everything in one shot)

```bash
#!/usr/bin/env bash
# Full end-to-end: health -> index -> search with proof.
# Usage: ./03-e2e.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost:8600}"

echo "== 1/3 health =="
curl -s "$BASE/v1/health" | python3 -m json.tool

echo ""
echo "== 2/3 index =="
./01-index.sh "$BASE"

echo ""
echo "== 3/3 search with proof =="
./02-search.sh "$BASE"
```

---

## Expected output

```text
== 1/3 health ==
{
    "status": "ok",
    "engine": "winnex-madhava 1.8.8",
    "tenants": ["liferay-1001"],
    ...
}

== 2/3 index ==
{
    "tenant_id": "liferay-1001",
    "indexed": 6,
    "dim": 32,
    "engine": "winnex-madhava 1.8.8"
}

== 3/3 search with proof ==
{
    "results": [
        {"external_id": "MTS-0001", ...},
        ...
    ],
    "bound_violations": 0,
    "bound_pairs": 6,
    "sound": true,
    "engine": "winnex-madhava 1.8.8",
    ...
}
== reading the proof ==
SOUND: 0 bound violations -- no relevant record was lost.
```

---

## Notes

- **The vectors are random** -- they only demonstrate the *mechanics* of the
  proof, not real retrieval quality. In production, replace them with real
  embeddings (BGE, BlueBERT, OpenAI, etc.).
- **bound_pairs = 6** here means the engine evaluated all 6 documents with a
  bound (a linear scan with proof at this tiny scale) -- exactly as the
  Tracer-MED spec documents honestly.
- Once the scripts work, the Liferay modules (examples 01-05) consume the
  same microservice through the OSGi bridge.

---

*Winnex AI -- BSL 1.1 . pay@winnex.ai . CNPJ 58.364.637/0001-47*
