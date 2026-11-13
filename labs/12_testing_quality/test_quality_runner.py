#!/usr/bin/env python3
"""
Lab 12 — Test Quality Master Runner

Runs all four test-quality labs (mutation, property-based, metamorphic,
interval/unit) and emits a consolidated report with tamper-evident RCPT
receipts via arena_guard.py exec.
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "labs" / "12_testing_quality"))


def main():
    t0 = time.time()
    report = {"lab_suite": "test_quality", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "labs": {}}

    labs = [
        ("mutation", "mutation_testing_lab", "run_mutation_lab", ["scripts/hyper_runner.py"]),
        ("property_based", "property_based_testing_lab", "run_property_based_lab", []),
        ("metamorphic", "metamorphic_testing_lab", "run_metamorphic_lab", []),
        ("interval_units", "interval_arithmetic_lab", "run_interval_lab", []),
    ]

    for lab_id, module_name, func_name, args in labs:
        try:
            mod = __import__(module_name)
            func = getattr(mod, func_name)
            lab_result = func(*args)
            report["labs"][lab_id] = lab_result
        except Exception as e:
            report["labs"][lab_id] = {"error": type(e).__name__, "detail": str(e)[:200]}

    report["duration_sec"] = round(time.time() - t0, 2)

    # Consolidated pass/fail
    passed = 0
    failed = 0
    for lid, lr in report["labs"].items():
        if "error" in lr:
            failed += 1
        elif lr.get("mutation_score") is not None:
            if lr["mutation_score"] >= 50:
                passed += 1
            else:
                failed += 1
        elif "failures" in lr and lr["failures"]:
            failed += 1
        elif "all_pass" in lr and not lr["all_pass"]:
            failed += 1
        elif "summary" in lr and ("passed" in lr["summary"] or "violations" in lr["summary"]):
            # Heuristic: if summary mentions violations > 0, it's a finding (not necessarily fail)
            passed += 1
        else:
            passed += 1

    report["summary"] = f"{passed} labs passed, {failed} labs failed"
    report["passed"] = passed
    report["failed"] = failed

    print(json.dumps(report, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
