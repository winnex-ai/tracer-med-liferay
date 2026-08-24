#!/usr/bin/env bash
# build-lpkg.sh - Builds the Tracer-MED distribution package (.lpkg).
#
# The .lpkg is a ZIP containing:
#   1. The 3 OSGi bundle JARs (API, Service, Portlet).
#   2. liferay-marketplace.properties (metadata, required-apps empty).
#   3. LICENSE (BSL 1.1) - NOT internal docs, NOT prompts, NOT secrets.
#
# Usage: ./scripts/build-lpkg.sh
#
# Winnex AI | Klenio Padilha | pay@winnex.ai | BSL 1.1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS_DIR="/opt/liferay/workspace"          # Liferay workspace inside the container
OUT_DIR="$ROOT/dist"
LPKG="$OUT_DIR/tracer-med-1.0.0.lpkg"

echo "==> Building module JARs in the Liferay container..."
docker exec tracer-med-liferay sh -c \
  "cd $WS_DIR && ./gradlew :modules:winnex-madhava-api:jar \
     :modules:winnex-madhava-service:jar :modules:winnex-tracer-med:jar --no-daemon" \
  >/dev/null 2>&1 || {
    echo "ERROR: gradle build failed. Is the Liferay container running?" >&2
    exit 1
  }

mkdir -p "$OUT_DIR"
rm -f "$LPKG"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# 1. Copy the 3 bundle JARs (clean OSGi artifacts only).
docker cp "tracer-med-liferay:$WS_DIR/modules/winnex-madhava-api/build/libs/com.winnex.madhava.api-1.0.0.jar" "$STAGE/"
docker cp "tracer-med-liferay:$WS_DIR/modules/winnex-madhava-service/build/libs/com.winnex.madhava.service-1.0.0.jar" "$STAGE/"
docker cp "tracer-med-liferay:$WS_DIR/modules/winnex-tracer-med/build/libs/com.winnex.tracermed-1.0.0.jar" "$STAGE/"

# 2. Marketplace metadata (self-contained: required-apps empty).
cat > "$STAGE/liferay-marketplace.properties" <<'PROP'
app.version=1.0.0
app.marketplace=true
app.title=Tracer-MED - Clinical Triage with Mathematical Proof
app.description=Clinical triage with Cauchy-Schwarz proven vector search (winnex-madhava). Soundness-guaranteed retrieval, ICD-10 metadata filtering, LGPD/GDPR/HIPAA compliance reports.
app.owner=Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
app.vendor=Winnex AI - Winnex Brasil Solucoes Empresariais LTDA (CNPJ 58.364.637/0001-47)
app.author=Winnex AI | Klenio Padilha
app.category=clinical
app.license=Business Source License 1.1 (BSL 1.1)
app.contact=pay@winnex.ai
app.homepage=https://winnex.ai
app.icon=https://winnex.ai/logo-petit_white.webp
app.thumbnail=https://winnex.ai/logo-petit_white.webp
required-apps=
PROP

# 3. License file (BSL 1.1) — from repo root (commercial grant included).
cp "$ROOT/LICENSE" "$STAGE/LICENSE"

# 4. End User License Agreement (Liferay Marketplace §5.5 — worldwide).
cp "$ROOT/EULA.md" "$STAGE/EULA.md"

# 5. Third-party notices (Liferay Marketplace §5.7 — OSS attribution).
cp "$ROOT/THIRD_PARTY_NOTICES.md" "$STAGE/THIRD_PARTY_NOTICES.md"

# 6. Sanity: reject any secret/dev-only/internal file that must not ship.
for forbidden in ".env" ".pem" ".key" ".crt" "secret" "credential" "autologin" "ANALISE" "ESTUDO" "PLANO" "PROMPT" "internal/"; do
  if find "$STAGE" -iname "*$forbidden*" -print -quit 2>/dev/null | grep -q .; then
    echo "ERROR: forbidden artifact '$forbidden' found in package." >&2
    exit 1
  fi
done

# 7. Assemble the .lpkg (ZIP) using Python (portable, no zip dependency).
python3 - "$STAGE" "$LPKG" <<'PY'
import os, sys, zipfile
stage, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in sorted(os.listdir(stage)):
        z.write(os.path.join(stage, name), arcname=name)
print("==> Package created: %s" % out)
PY

echo ""
echo "==> Package contents:"
python3 - "$LPKG" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    for i in z.infolist():
        print("  %s  (%d bytes)" % (i.filename, i.file_size))
PY
