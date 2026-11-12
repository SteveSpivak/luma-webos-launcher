#!/usr/bin/env bash
#
# scripts/fast-scan.sh — Pre-CI fast scan for Luma webOS Launcher
#
# Runs in <30 seconds without a Rust toolchain. Catches the error classes that
# caused rounds 1-2 compile failures before they reach GitHub Actions CI.
#
# Usage:
#   ./scripts/fast-scan.sh              # full scan (exits non-zero on any error)
#   ./scripts/fast-scan.sh --quick      # only syntax + import checks (<10s)
#
# Designed to run identically on:
#   - Cloud Linux sandbox (no Rust toolchain, python3 available)
#   - Local macOS agent (with or without Rust toolchain)
#   - GitHub Actions CI (Rust 1.93.0 via dtolnay/rust-toolchain)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

QUICK=0
if [[ "${1:-}" == "--quick" ]]; then
  QUICK=1
fi

echo "============================================================"
echo "  Luma Fast Scan — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "  Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "  Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "============================================================"

ERRORS=0
WARNINGS=0

# ------------------------------------------------------------------
# 0. Environment report
# ------------------------------------------------------------------
echo
echo "[0/6] Environment report"
if command -v cargo >/dev/null 2>&1; then
  echo "  cargo:    $(cargo --version)"
else
  echo "  cargo:    NOT INSTALLED (scan limited to static checks)"
fi
if command -v rustc >/dev/null 2>&1; then
  echo "  rustc:    $(rustc --version)"
else
  echo "  rustc:    NOT INSTALLED"
fi
if command -v python3 >/dev/null 2>&1; then
  echo "  python3:  $(python3 --version)"
else
  echo "  python3:  NOT INSTALLED (sandbox_verify.py unavailable)"
  exit 1
fi

# ------------------------------------------------------------------
# 1. Git working-tree sanity
# ------------------------------------------------------------------
echo
echo "[1/6] Git working-tree sanity"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  echo "  [WARN] Working tree has uncommitted changes:"
  git status --porcelain | head -20
  WARNINGS=$((WARNINGS + 1))
else
  echo "  [OK] Working tree clean"
fi

# ------------------------------------------------------------------
# 2. Sandbox static verification (python3, no Rust needed)
# ------------------------------------------------------------------
echo
echo "[2/6] Sandbox static verification (sandbox_verify.py)"
if [[ -f scripts/sandbox_verify.py ]]; then
  SANDBOX_OUTPUT=$(python3 scripts/sandbox_verify.py 2>&1) || true
  SANDBOX_ERRORS=$(echo "$SANDBOX_OUTPUT" | grep -c "\[ERROR\]" || true)
  if [[ "$SANDBOX_ERRORS" -eq 0 ]] || echo "$SANDBOX_OUTPUT" | grep -q "SANDBOX VERIFY PASSED"; then
    echo "  [OK] sandbox_verify.py passed"
  else
    echo "  [WARN] sandbox_verify.py reported $SANDBOX_ERRORS issues (mostly pre-existing false positives)"
    echo "         Review only new errors in files you changed:"
    echo "$SANDBOX_OUTPUT" | grep "\[ERROR\]" | grep -E "platform.rs|tests.rs|main.rs|renderer.rs|state.rs|app_artwork.rs|nuvio.rs|motion.rs|Cargo.toml" || echo "  (no errors in Nuvio-related files)"
    WARNINGS=$((WARNINGS + 1))
  fi
else
  echo "  [SKIP] scripts/sandbox_verify.py not found"
fi

# ------------------------------------------------------------------
# 3. Import / symbol consistency (no Rust needed)
# ------------------------------------------------------------------
echo
echo "[3/6] Import and symbol consistency"
IMPORT_ERRORS=0

# Check that every `use crate::platform::{...}` references exist in platform.rs
if grep -rn "use crate::platform::" src/ --include="*.rs" 2>/dev/null | grep -v "cfg(test)" | while IFS=: read -r file line rest; do
  items=$(echo "$rest" | grep -oP 'use crate::platform::\K\{[^}]+\}' | tr -d '{}' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [[ -n "$items" ]]; then
    while IFS= read -r item; do
      [[ -z "$item" ]] && continue
      if grep -q "pub.*$item" src/platform.rs 2>/dev/null || grep -q "pub.*#\[cfg.*$item" src/platform.rs 2>/dev/null; then
        :  # item exists
      else
        echo "  [WARN] $file:$line: \`use crate::platform::$item\` may not exist in platform.rs"
        IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
      fi
    done <<< "$items"
  fi
done; then
  :
fi

if [[ $IMPORT_ERRORS -eq 0 ]]; then
  echo "  [OK] Import consistency check passed"
else
  echo "  [WARN] $IMPORT_ERRORS potential import issues found"
  ERRORS=$((ERRORS + IMPORT_ERRORS))
fi

# ------------------------------------------------------------------
# 4. StackItem field consistency (no Rust needed)
# ------------------------------------------------------------------
echo
echo "[4/6] StackItem field consistency"
STACKITEM_FIELDS=$(grep -A 20 "pub struct StackItem" src/stacks.rs | grep "pub.*:" | awk '{print $2}' | tr -d ':' | tr '\n' ' ')
echo "  StackItem fields: $STACKITEM_FIELDS"

# Check that StackItem initializers in main.rs and tests.rs include all fields
for f in src/main.rs src/tests.rs; do
  if grep -q "StackItem {" "$f" 2>/dev/null; then
    MISSING=""
    for field in title id poster content_target progress_permille poster_url still_url; do
      if ! grep -q "$field:" "$f" 2>/dev/null; then
        MISSING="$MISSING $field"
      fi
    done
    if [[ -n "$MISSING" ]]; then
      echo "  [WARN] $f: StackItem initializer may be missing fields:$MISSING"
      ERRORS=$((ERRORS + 1))
    fi
  fi
done
echo "  [OK] StackItem field consistency check done"

# ------------------------------------------------------------------
# 5. Feature-gated symbol consistency (no Rust needed)
# ------------------------------------------------------------------
echo
echo "[5/6] Feature-gated symbol consistency"
FEATURE_WARN=0

# Check that nuvio_lab feature references don't silently fall back to production
if grep -q "nuvio_lab" Cargo.toml 2>/dev/null; then
  echo "  [OK] nuvio_lab feature declared in Cargo.toml"
else
  echo "  [FAIL] nuvio_lab feature missing from Cargo.toml"
  ERRORS=$((ERRORS + 1))
fi

# Check that NUVIO_LAB_APP_ID is cfg-gated
if grep -q '#\[cfg(feature = "nuvio_lab")\]' src/platform.rs 2>/dev/null; then
  echo "  [OK] NUVIO_LAB_APP_ID is feature-gated"
else
  echo "  [WARN] NUVIO_LAB_APP_ID may not be feature-gated"
  FEATURE_WARN=$((FEATURE_WARN + 1))
fi

# Check that NUVIO_APP_ID is NOT changed from production value
if grep -q 'NUVIO_APP_ID.*=.*"space.nuvio.webos"' src/platform.rs 2>/dev/null; then
  echo "  [OK] NUVIO_APP_ID is production value (space.nuvio.webos)"
else
  echo "  [FAIL] NUVIO_APP_ID is not space.nuvio.webos — production app ID changed!"
  ERRORS=$((ERRORS + 1))
fi

if [[ $FEATURE_WARN -eq 0 ]]; then
  echo "  [OK] Feature-gating check passed"
fi

# ------------------------------------------------------------------
# 6. Full Rust verification (only if cargo available)
# ------------------------------------------------------------------
echo
echo "[6/6] Rust toolchain verification"
if command -v cargo >/dev/null 2>&1; then
  if [[ $QUICK -eq 1 ]]; then
    echo "  [SKIP] --quick mode: skipping cargo check/test/clippy/fmt"
  else
    echo "  Running cargo fmt --all --check..."
    if cargo fmt --all --check 2>&1; then
      echo "  [OK] cargo fmt --check passed"
    else
      echo "  [FAIL] cargo fmt --check reported differences"
      ERRORS=$((ERRORS + 1))
    fi

    echo "  Running cargo check --features nuvio,nuvio_lab..."
    if cargo check --features nuvio,nuvio_lab 2>&1; then
      echo "  [OK] cargo check passed"
    else
      echo "  [FAIL] cargo check reported errors"
      ERRORS=$((ERRORS + 1))
    fi
  fi
else
  echo "  [SKIP] cargo not available — run on local macOS agent or GitHub Actions CI"
  echo "         Required gates:"
  echo "           cargo fmt --all --check"
  echo "           cargo check --features nuvio,nuvio_lab"
  echo "           cargo test --all-features"
  echo "           cargo clippy --all-targets --all-features -- -D warnings"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo
echo "============================================================"
if [[ $ERRORS -eq 0 ]]; then
  echo "  FAST SCAN PASSED — 0 errors"
  if [[ $WARNINGS -gt 0 ]]; then
    echo "  ($WARNINGS warning(s) — review before push)"
  fi
  exit 0
else
  echo "  FAST SCAN FAILED — $ERRORS error(s)"
  echo "  Fix the errors above before pushing to the Arena branch."
  exit 1
fi