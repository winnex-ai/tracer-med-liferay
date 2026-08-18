#!/usr/bin/env bash
# Full end-to-end against the Madhava microservice.
# Usage: ./03-e2e.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost:8600}"

echo "== 1/3 health =="
curl -s "$BASE/v1/health" | python3 -m json.tool

echo ""
echo "== 2/3 index =="
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
print(json.dumps({"tenant_id": "liferay-1001", "k": 5, "corpus": [
    {"external_id": eid, "vector": unit(), "metadata": {"cid10": cid, "text": txt}}
    for eid, cid, txt in docs]}))
PY
curl -s -X POST "$BASE/v1/index" -H "Content-Type: application/json" \
  -d @/tmp/tracer-med-corpus.json | python3 -m json.tool

echo ""
echo "== 3/3 search with proof =="
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
RESP=$(curl -s -X POST "$BASE/v1/search" -H "Content-Type: application/json" \
  -d @/tmp/tracer-med-query.json)
echo "$RESP" | python3 -m json.tool

echo ""
echo "== reading the proof =="
if echo "$RESP" | grep -qE '"bound_violations": ?0|"sound":true'; then
  echo "SOUND: 0 bound violations -- no relevant record was lost."
else
  echo "BOUND VIOLATION -- investigate!"
fi
