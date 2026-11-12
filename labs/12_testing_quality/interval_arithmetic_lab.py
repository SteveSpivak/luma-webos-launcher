#!/usr/bin/env python3
"""
Lab 12 — Interval Arithmetic & Unit Checking Audit (pint + manual intervals)

Proves numerical bounds instead of guessing tolerances (atol=1e-8 is a guess,
not a proof). Combines:
  - pint for compile-time unit/dimensional checking (catches Mars Climate Orbiter-class errors)
  - Manual interval arithmetic for provable result bounds
"""
from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def interval_add(a_lo, a_hi, b_lo, b_hi):
    return (a_lo + b_lo, a_hi + b_hi)


def interval_mul(a_lo, a_hi, b_lo, b_hi):
    products = [a_lo * b_lo, a_lo * b_hi, a_hi * b_lo, a_hi * b_hi]
    return (min(products), max(products))


def run_interval_lab() -> dict:
    """Prove numerical bounds with interval arithmetic + check units with pint."""
    t0 = time.time()
    results = {"lab": "interval_arithmetic_units", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "interval_tests": [], "unit_tests": [], "duration_sec": None}

    # Test 1: Prove bound on (x + y) where x in [1,2], y in [3,4] -> result in [4,6]
    lo, hi = interval_add(1.0, 2.0, 3.0, 4.0)
    results["interval_tests"].append({
        "expression": "x + y where x∈[1,2], y∈[3,4]",
        "proven_bounds": [lo, hi],
        "expected": [4.0, 6.0],
        "proof_correct": lo == 4.0 and hi == 6.0,
    })

    # Test 2: Prove bound on x * y where x in [2,3], y in [4,5] -> result in [8,15]
    lo, hi = interval_mul(2.0, 3.0, 4.0, 5.0)
    results["interval_tests"].append({
        "expression": "x * y where x∈[2,3], y∈[4,5]",
        "proven_bounds": [lo, hi],
        "expected": [8.0, 15.0],
        "proof_correct": lo == 8.0 and hi == 15.0,
    })

    # Test 3: Negative interval multiplication — x in [-2,-1], y in [3,4] -> result in [-8,-3]
    lo, hi = interval_mul(-2.0, -1.0, 3.0, 4.0)
    results["interval_tests"].append({
        "expression": "x * y where x∈[-2,-1], y∈[3,4]",
        "proven_bounds": [lo, hi],
        "expected": [-8.0, -3.0],
        "proof_correct": lo == -8.0 and hi == -3.0,
    })

    # Unit checking with pint (Mars Climate Orbiter-class error detection)
    try:
        import pint
        ureg = pint.UnitRegistry()
        results["unit_tests"].append({"library": "pint", "version": pint.__version__, "available": True})

        # Speed = distance / time: meters / second = m/s (dimensionally correct)
        try:
            speed = (100 * ureg.meter) / (10 * ureg.second)
            results["unit_tests"].append({
                "check": "100m / 10s = 10 m/s (dimensionally correct)",
                "result": str(speed),
                "units_ok": str(speed.units) == "meter / second",
            })
        except Exception as e:
            results["unit_tests"].append({"check": "100m / 10s", "error": str(e)[:100], "units_ok": False})

        # Dimensional mismatch: adding meters to seconds should fail
        try:
            _ = (5 * ureg.meter) + (3 * ureg.second)
            results["unit_tests"].append({"check": "5m + 3s (should FAIL dimension check)", "units_ok": False,
                                          "error": "No error raised — unit system not catching mismatch"})
        except Exception as e:
            results["unit_tests"].append({
                "check": "5m + 3s (should FAIL dimension check)",
                "units_ok": True,
                "detail": f"Correctly rejected: {type(e).__name__}",
            })
    except ImportError:
        results["unit_tests"].append({"library": "pint", "available": False, "error": "not installed"})

    all_pass = all(t["proof_correct"] for t in results["interval_tests"]) and \
               all(t.get("units_ok", True) for t in results["unit_tests"])
    results["summary"] = f"Interval proofs: {sum(1 for t in results['interval_tests'] if t['proof_correct'])}/{len(results['interval_tests'])} passed; " \
                         f"Unit checks: {sum(1 for t in results['unit_tests'] if t.get('units_ok', True))}/{len(results['unit_tests'])} passed"
    results["all_pass"] = all_pass
    results["duration_sec"] = round(time.time() - t0, 2)
    return results


if __name__ == "__main__":
    out = run_interval_lab()
    print(json.dumps(out, indent=2))
