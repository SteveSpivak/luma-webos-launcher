#!/usr/bin/env bash
#
# Lab 1: Compile Gate Reproducer
#
# Reproduces all 5 CI gates locally. Requires a Rust toolchain.
# Run on local macOS agent or GitHub Actions CI.
#
# Usage: ./run.sh [--quick]
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

QUICK=0
if [[ "${1:-}" == "--quick" ]]; then
  QUICK=1
fi

echo "============================================================"
echo "  Lab 1: Compile Gate Reproducer"
echo "  Repo: $REPO_ROOT"
echo "  Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo "============================================================"

if ! command -v cargo >/dev/null 2>&1; then
  echo "ERROR: cargo not found. Install Rust: https://rustup.rs/"
  echo "       Or run in GitHub Actions CI (Rust 1.93.0 via dtolnay/rust-toolchain)"
  exit 1
fi

echo "cargo: $(cargo --version)"
echo "rustc: $(rustc --version)"

FAILURES=0

run_gate() {
  local name="$1"
  local cmd="$2"
  echo
  echo "--- Gate: $name ---"
  echo "  $cmd"
  if eval "$cmd"; then
    echo "  [PASS] $name"
  else
    echo "  [FAIL] $name"
    FAILURES=$((FAILURES + 1))
  fi
}

run_gate "Format check" "cargo fmt --all --check"

if [[ $QUICK -eq 0 ]]; then
  run_gate "Check (nuvio,nuvio_lab)" "cargo check --features nuvio,nuvio_lab"
  run_gate "Test build (no-run, all-features)" "cargo test --no-run --all-features"
  run_gate "Clippy (all targets, all features, -D warnings)" "cargo clippy --all-targets --all-features -- -D warnings"
  run_gate "Test run (all-features)" "cargo test --all-features"
else
  echo "  [SKIP] --quick mode: skipping full cargo gates"
fi

echo
echo "============================================================"
if [[ $FAILURES -eq 0 ]]; then
  echo "  LAB 1 PASSED — All gates green"
  exit 0
else
  echo "  LAB 1 FAILED — $FAILURES gate(s) failed"
  exit 1
fi