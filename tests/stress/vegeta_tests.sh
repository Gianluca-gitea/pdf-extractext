#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PDF_DIR="$(dirname "$0")/pdfs"

targets=$(mktemp)
trap 'rm -f "$targets"' EXIT

for pdf in "$PDF_DIR"/*.pdf; do
    printf 'POST %s/extract\nContent-Type: application/pdf\n@%s\n\n' "$BASE_URL" "$pdf" >> "$targets"
done

echo "[INFO] Atacando $BASE_URL/extract a 50 req/s durante 30s (timeout 30s) con $(grep -c '^POST' "$targets") PDFs"

vegeta attack -targets="$targets" -rate=50 -duration=30s -timeout=30s | vegeta report
