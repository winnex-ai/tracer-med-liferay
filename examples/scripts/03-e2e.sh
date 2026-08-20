#!/usr/bin/env bash
# Full end-to-end: Liferay bridge → winnex-ai-normalize (provider registration
# + text embedding) → winnex-madhava → winnex-tracer commitment.
# Uses REAL data and REAL embedding providers (bge-m3 local / Qwen3).
#
# Usage: ./03-e2e.sh [base_url] [embedding_url] [embedding_model] [admin_key]
set -euo pipefail
BASE="${1:-http://localhost:8600}"
EMB_URL="${2:-http://localhost:8102}"       # the embedding service (bge-m3 / Qwen3)
EMB_MODEL="${3:-BAAI/bge-m3}"
ADMIN_KEY="${4:-change-me-in-production}"
AUTH="X-Winnex-Api-Key: change-me-in-production"

echo "== 1/5 health =="
curl -s "$BASE/v1/health" | python3 -m json.tool

echo ""
echo "== 2/5 register embedding provider (via the Liferay form contract) =="
curl -s -X POST "$BASE/v1/normalize/providers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -d "{\"name\": \"qwen3\", \"base_url\": \"$EMB_URL\", \"model\": \"$EMB_MODEL\", \"dim\": 1024, \"priority\": 1}" | python3 -m json.tool

echo ""
echo "== 3/5 normalize real clinical text → vectors (winnex-ai-normalize) =="
python3 - "$BASE" <<'PY' > /tmp/tracer-med-embed.json
import sys, json, urllib.request
base = sys.argv[1]
docs = [
    "Patient with essential hypertension, BP 150/95. ACE inhibitor therapy.",
    "Type 2 diabetes mellitus. HbA1c 8.2 percent. Metformin 500mg.",
    "Cardiac evaluation, ECG normal sinus rhythm. No ischemia.",
    "Hyperlipidemia, LDL 160 mg/dL. Recommend statin therapy.",
    "Chronic kidney disease stage 3, eGFR 45. Monitor creatinine.",
]
req = urllib.request.Request(f"{base}/v1/normalize/embed",
    data=json.dumps({"input": docs}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.loads(resp.read())
print(json.dumps({"tenant_id": "liferay-1001", "k": 5, "corpus": [
    {"external_id": f"CL-{i}", "vector": d["data"][i]["embedding"],
     "metadata": {"text": docs[i], "cid10": "I10" if "hyper" in docs[i].lower() else "E78"}}
    for i in range(len(docs))]}))
PY
python3 -c "
import json
d = json.load(open('/tmp/tracer-med-embed.json'))
print(f'  {len(d[\"corpus\"])} documentos normalizados (d={len(d[\"corpus\"][0][\"vector\"])})')
"

echo ""
echo "== 4/5 index + search with proof (winnex-madhava + commitment) =="
curl -s -X POST "$BASE/v1/index" -H "Content-Type: application/json" -H "$AUTH" \
  -d @/tmp/tracer-med-embed.json | python3 -m json.tool

python3 - "$BASE" <<'PY' > /tmp/tracer-med-query.json
import sys, json, urllib.request
base = sys.argv[1]
req = urllib.request.Request(f"{base}/v1/normalize/embed",
    data=json.dumps({"input": ["blood pressure medication effectiveness"]}).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.loads(resp.read())
print(json.dumps({"query": d["data"][0]["embedding"], "tenant_id": "liferay-1001", "k": 3}))
PY
RESP=$(curl -s -X POST "$BASE/v1/search" -H "Content-Type: application/json" -H "$AUTH" \
  -d @/tmp/tracer-med-query.json)
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('results    :', [r['external_id'] for r in d.get('results', [])][:3])
print('violations :', d['bound_violations'], '| sound:', d['sound'])
print('excluded   :', d.get('audit_excluded'))
print('engine     :', d['engine'])
"

echo ""
echo "== 5/5 verify certificate (QR endpoint) =="
echo "  (the /verify?tenant=&hash= endpoint validates the signed commitment)"
echo "  -> see examples/07-qr-certificate for the QR flow"
