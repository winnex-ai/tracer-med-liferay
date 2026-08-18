#!/usr/bin/env bash
# Sobe o ambiente Tracer-MED × Liferay (Fase 1: Liferay + Postgres).
# Fase 2: adiciona o serviço de ponte Madhava ao compose.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/liferay/docker-compose.yml"

mkdir -p "$ROOT/liferay/volumes/deploy" "$ROOT/liferay/volumes/data"

echo "==> Subindo Liferay + Postgres (imagem oficial 7.4.3.132-ga132) ..."
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Aguardando o portal (primeira subida pode levar minutos) ..."
for i in $(seq 1 40); do
  if curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8080 2>/dev/null | grep -qE "200|302|401"; then
    echo "==> Portal no ar: http://localhost:8080 (após ${i}0s)"
    docker compose -f "$COMPOSE_FILE" ps
    exit 0
  fi
  sleep 10
done

echo "!!> Portal ainda não respondeu. Logs:"
docker compose -f "$COMPOSE_FILE" logs --tail=50 liferay
exit 1
