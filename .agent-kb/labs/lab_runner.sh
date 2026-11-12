#!/usr/bin/env bash
#
# lab_runner.sh — Run all executable verification labs
#
# Usage:
#   ./lab_runner.sh              # Run all labs
#   ./lab_runner.sh 01           # Run only Lab 1
#   ./lab_runner.sh 02           # Run only Lab 2
#   ./lab_runner.sh 03           # Run only Lab 3
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LAB="${1:-all}"

echo "============================================================"
echo "  Luma Verification Labs"
echo "  Repo: $REPO_ROOT"
echo "============================================================"

FAILURES=0

run_lab() {
  local num="$1"
  local dir="$2"
  local cmd="$3"
  echo
  echo "============================================================"
  echo "  Lab $num: $dir"
  echo "============================================================"
  if eval "$cmd"; then
    echo "  [PASS] Lab $num"
  else
    echo "  [FAIL] Lab $num"
    FAILURES=$((FAILURES + 1))
  fi
}

if [[ "$LAB" == "all" || "$LAB" == "01" ]]; then
  run_lab "1" "compile_gate" "bash .agent-kb/labs/01_compile_gate/run.sh --quick"
fi

if [[ "$LAB" == "all" || "$LAB" == "02" ]]; then
  run_lab "2" "lckv_fixture" "python3 .agent-kb/labs/02_lckv_fixture/generate.py golden-436 tombstone-40 truncated odd-seq"
fi

if [[ "$LAB" == "all" || "$LAB" == "03" ]]; then
  run_lab "3" "nuvio_deeplink" "python3 .agent-kb/labs/03_nuvio_deeplink/trace.py"
fi

echo
echo "============================================================"
if [[ $FAILURES -eq 0 ]]; then
  echo "  ALL LABS PASSED"
  exit 0
else
  echo "  $FAILURES LAB(S) FAILED"
  exit 1
fi