#!/bin/sh
# scripts/sync-docs.sh — Regenerate hash-verified doc mirrors from source of truth.
# Source of truth: docs/xray/*.md  (never edit mirrors directly)
# Mirrors: MANIFEST.sha256 + optional archive branch (archive/docs-YYYYMMDD)
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

MANIFEST="MANIFEST.sha256"
DATA_DIR="docs/xray/_data"

echo "[sync-docs] Rebuilding MANIFEST.sha256 from docs/xray/ source of truth..."

{
  echo "# MANIFEST.sha256 — Doc provenance mirror manifest (L6)"
  echo "# Format: <sha256>  <path>  <last-verified-commit>  <refresh-trigger>  <owner>"
  echo "# Rule: edit only the source of truth in docs/xray/; regenerate mirrors via"
  echo "# scripts/sync-docs.sh. Two edited copies = drift = defect."
  echo ""
  LAST_COMMIT="$(git rev-parse --short HEAD)"
  for md in docs/xray/*.md docs/xray/**/*.md; do
    [ -f "$md" ] || continue
    SHA="$(sha256sum "$md" | awk '{print $1}')"
    echo "${SHA}  ${md}  ${LAST_COMMIT}  on-any-docs-xray-change  Arena-Cloud-Agent"
  done
} > "$MANIFEST"

echo "[sync-docs] MANIFEST.sha256 regenerated with $(grep -c '  docs/xray/' "$MANIFEST") entries."

# Verify every manifest entry resolves to an existing file
echo "[sync-docs] Verifying manifest integrity..."
awk '{print $2}' "$MANIFEST" | grep 'docs/xray/' | while read -r p; do
  if [ ! -f "$p" ]; then
    echo "[sync-docs] ERROR: manifest entry missing on disk: $p" >&2
    exit 1
  fi
done
echo "[sync-docs] Manifest integrity OK."
